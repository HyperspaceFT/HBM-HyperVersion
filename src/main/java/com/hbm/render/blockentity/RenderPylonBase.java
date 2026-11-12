package com.hbm.render.blockentity;

import com.hbm.blockentity.network.PylonBaseBlockEntity;
import com.hbm.blocks.DummyableBlock;
import com.hbm.config.NtmConfig;
import com.hbm.main.ResourceManager;
import com.hbm.render.util.RenderContext;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import net.minecraft.client.renderer.LevelRenderer;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.renderer.texture.OverlayTexture;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;

/**
 * The wires of pylons, connectors and substations (original RenderPylonBase.java:16-202). Each end draws half of every wire, from
 * its mount to the midpoint, so a wire shows only where its other end's block entity is loaded on the client, as in the original.
 */
public abstract class RenderPylonBase<T extends PylonBaseBlockEntity> extends BlockEntityRendererNT<T> {

    /** Pairs this pylon's mounts with the other end's and draws half of each wire (RenderPylonBase.java:26-79). */
    public void renderLinesGeneric(T pyl, MultiBufferSource buffer) {

        Level level = pyl.getLevel();
        if(level == null) return;

        VertexConsumer consumer = buffer.getBuffer(RenderType.entityCutoutNoCull(pyl.color == 0 ? ResourceManager.WIRE_TEX : ResourceManager.WIRE_GREYSCALE_TEX));
        BlockPos pos = pyl.getBlockPos();

        for(BlockPos wire : pyl.getConnected()) {

            BlockEntity be = level.getBlockEntity(wire);
            if(!(be instanceof PylonBaseBlockEntity pylon)) continue;

            Vec3[] m1 = pyl.getMountPos();
            Vec3[] m2 = pylon.getMountPos();

            int lineCount = Math.min(m1.length, m2.length);

            for(int line = 0; line < lineCount; line++) {

                Vec3 first = m1[line % m1.length];
                int secondIndex = line % m2.length;

                // The original's shift by two so that wires between a north- and an east-facing four-wire pylon do not cross
                if(lineCount == 4) {
                    Direction a = pyl.getBlockState().getValue(DummyableBlock.FACING);
                    Direction b = pylon.getBlockState().getValue(DummyableBlock.FACING);
                    if((a == Direction.EAST && b == Direction.NORTH) || (a == Direction.NORTH && b == Direction.EAST)) {
                        secondIndex += 2;
                        secondIndex %= m2.length;
                    }
                }

                Vec3 second = m2[secondIndex];

                double sX = second.x + wire.getX() - pos.getX();
                double sY = second.y + wire.getY() - pos.getY();
                double sZ = second.z + wire.getZ() - pos.getZ();

                this.renderLine(level, pyl, consumer,
                        first.x, first.y, first.z,
                        first.x + (sX - first.x) * 0.5,
                        first.y + (sY - first.y) * 0.5,
                        first.z + (sZ - first.z) * 0.5);
            }
        }
    }

    /**
     * Half a wire from the mount (x0, y0, z0) to the midpoint (x1, y1, z1), relative to the block's corner: ten segments sagging by
     * sin(j / 10 * pi / 2) * min(length / 15, 2.5), lit per segment, or one straight segment with the client option off
     * (RenderPylonBase.java:96-149).
     */
    public void renderLine(Level level, T pyl, VertexConsumer consumer, double x0, double y0, double z0, double x1, double y1, double z1) {

        float count = 10;
        PoseStack.Pose pose = RenderContext.poseStack().last();
        BlockPos pos = pyl.getBlockPos();
        int color = pyl.color == 0 ? 0xffffff : pyl.color;

        double dX = x0 - x1, dY = y0 - y1, dZ = z0 - z1;

        double girth = 0.03125D;
        double hyp = Math.sqrt(dX * dX + dZ * dZ);
        double yaw = Math.atan2(dX, dZ);
        double pitch = Math.atan2(dY, hyp);
        double rotator = Math.PI * 0.5D;
        double newPitch = pitch + rotator;
        double newYaw = yaw + rotator;
        double iZ = Math.cos(yaw) * Math.cos(newPitch) * girth;
        double iX = Math.sin(yaw) * Math.cos(newPitch) * girth;
        double iY = Math.sin(newPitch) * girth;
        double jZ = Math.cos(newYaw) * girth;
        double jX = Math.sin(newYaw) * girth;

        if(!NtmConfig.CLIENT.RENDER_CABLE_HANG.get()) {
            int light = light(level, pos, (x0 + x1) * 0.5, (y0 + y1) * 0.5, (z0 + z1) * 0.5);
            this.drawLineSegment(consumer, pose, color, light, x0, y0, z0, x1, y1, z1, iX, iY, iZ, jX, jZ);
        } else {

            double hang = Math.min(Math.sqrt(dX * dX + dY * dY + dZ * dZ) / 15D, 2.5D);

            for(float j = 0; j < count; j++) {

                float k = j + 1;

                double sagJ = Math.sin(j / count * Math.PI * 0.5) * hang;
                double sagK = Math.sin(k / count * Math.PI * 0.5) * hang;
                double sagMean = (sagJ + sagK) / 2D;

                double deltaX = x1 - x0;
                double deltaY = y1 - y0;
                double deltaZ = z1 - z0;

                double ja = j + 0.5D;
                int light = light(level, pos, x0 + deltaX / count * ja, y0 + deltaY / count * ja - sagMean, z0 + deltaZ / count * ja);

                this.drawLineSegment(consumer, pose, color, light,
                        x0 + (deltaX * j / count),
                        y0 + (deltaY * j / count) - sagJ,
                        z0 + (deltaZ * j / count),
                        x0 + (deltaX * k / count),
                        y0 + (deltaY * k / count) - sagK,
                        z0 + (deltaZ * k / count),
                        iX, iY, iZ, jX, jZ);
            }
        }
    }

    private static int light(Level level, BlockPos origin, double x, double y, double z) {
        BlockPos at = BlockPos.containing(origin.getX() + x, origin.getY() + y, origin.getZ() + z);
        return level.hasChunkAt(at) ? LevelRenderer.getLightColor(level, at) : RenderContext.light();
    }

    /** Two crossed quads from (x, y, z) to (a, b, c), the texture repeated every eighth of a block (RenderPylonBase.java:162-200). */
    public void drawLineSegment(VertexConsumer consumer, PoseStack.Pose pose, int color, int light, double x, double y, double z, double a, double b, double c, double iX, double iY, double iZ, double jX, double jZ) {

        double deltaX = a - x;
        double deltaY = b - y;
        double deltaZ = c - z;
        double length = Math.sqrt(deltaX * deltaX + deltaY * deltaY + deltaZ * deltaZ);
        int wrap = (int) Math.ceil(length * 8);

        if(deltaX + deltaZ < 0) {
            wrap *= -1;
            jZ *= -1;
            jX *= -1;
        }

        vertex(consumer, pose, color, light, x + iX, y + iY, z + iZ, 0, 0);
        vertex(consumer, pose, color, light, x - iX, y - iY, z - iZ, 0, 1);
        vertex(consumer, pose, color, light, a - iX, b - iY, c - iZ, wrap, 1);
        vertex(consumer, pose, color, light, a + iX, b + iY, c + iZ, wrap, 0);
        vertex(consumer, pose, color, light, x + jX, y, z + jZ, 0, 0);
        vertex(consumer, pose, color, light, x - jX, y, z - jZ, 0, 1);
        vertex(consumer, pose, color, light, a - jX, b, c - jZ, wrap, 1);
        vertex(consumer, pose, color, light, a + jX, b, c + jZ, wrap, 0);
    }

    private static void vertex(VertexConsumer consumer, PoseStack.Pose pose, int color, int light, double x, double y, double z, float u, float v) {
        consumer.addVertex(pose, (float) x, (float) y, (float) z)
                .setColor((color >> 16) & 0xFF, (color >> 8) & 0xFF, color & 0xFF, 0xFF)
                .setUv(u, v)
                .setOverlay(OverlayTexture.NO_OVERLAY)
                .setLight(light)
                .setNormal(pose, 0F, 1F, 0F);
    }

    /** The wires reach far beyond the block (TileEntityPylonBase.java:189-198). */
    @Override
    public AABB getRenderBoundingBox(T be) {
        return AABB.INFINITE;
    }

    @Override public boolean shouldRenderOffScreen(T be) { return true; }
}
