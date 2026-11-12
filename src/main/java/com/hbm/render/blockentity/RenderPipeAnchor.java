package com.hbm.render.blockentity;

import com.hbm.blockentity.network.PipeAnchorBlockEntity;
import com.hbm.blocks.NtmBlocks;
import com.hbm.main.ResourceManager;
import com.hbm.render.item.ItemRenderBase;
import com.hbm.render.util.RenderContext;
import com.mojang.math.Axis;
import net.minecraft.client.renderer.BlockEntityWithoutLevelRenderer;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.blockentity.BlockEntityRenderer;
import net.minecraft.core.BlockPos;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;

/**
 * Pipe anchor and its pipes (original RenderPipeAnchor.java:19-136). Only the dominant end of a pipe, the one at the smaller
 * coordinates, draws it, and only while the other end is loaded on the client. The pipe takes the fluid colour lightened by a
 * quarter.
 */
public class RenderPipeAnchor extends BlockEntityRendererNT<PipeAnchorBlockEntity> implements IBEWLRProvider {

    @Override public BlockEntityRenderer<PipeAnchorBlockEntity> create(Context context) { return new RenderPipeAnchor(); }

    @Override
    public void render(PipeAnchorBlockEntity anchor, MultiBufferSource buffer, float partialTicks) {

        RenderContext.pushPose();
        RenderContext.translate(0.5F, 0.5F, 0.5F);

        RenderContext.pushPose();
        switch(anchor.getOppositeDir().getOpposite()) {
            case DOWN -> RenderContext.mulPose(Axis.XP.rotationDegrees(180F));
            case NORTH -> { RenderContext.mulPose(Axis.XP.rotationDegrees(90F)); RenderContext.mulPose(Axis.ZP.rotationDegrees(180F)); }
            case SOUTH -> RenderContext.mulPose(Axis.XP.rotationDegrees(90F));
            case WEST -> { RenderContext.mulPose(Axis.XP.rotationDegrees(90F)); RenderContext.mulPose(Axis.ZP.rotationDegrees(90F)); }
            case EAST -> { RenderContext.mulPose(Axis.XP.rotationDegrees(90F)); RenderContext.mulPose(Axis.ZP.rotationDegrees(270F)); }
            default -> { }
        }
        RenderContext.translate(0F, -0.5F, 0F);
        bindTexture(ResourceManager.PIPE_ANCHOR_TEX);
        ResourceManager.pipe_anchor.renderPart("Anchor");
        RenderContext.popPose();

        Level level = anchor.getLevel();
        if(level != null) this.renderPipes(anchor, level);

        RenderContext.popPose();
    }

    private void renderPipes(PipeAnchorBlockEntity anchor, Level level) {

        Vec3 anchorPoint = anchor.getConnectionPoint();

        for(BlockPos pos : anchor.getConnected()) {

            BlockEntity be = level.getBlockEntity(pos);
            if(!(be instanceof PipeAnchorBlockEntity other)) continue;

            Vec3 connectionPoint = other.getConnectionPoint();
            if(!isDominant(anchorPoint, connectionPoint)) continue;

            double dX = connectionPoint.x - anchorPoint.x;
            double dY = connectionPoint.y - anchorPoint.y;
            double dZ = connectionPoint.z - anchorPoint.z;

            double hyp = Math.sqrt(dX * dX + dZ * dZ);
            double yaw = Math.toDegrees(Math.atan2(dX, dZ));
            double pitch = Math.toDegrees(Math.atan2(dY, hyp));
            double length = Math.sqrt(dX * dX + dY * dY + dZ * dZ);

            RenderContext.pushPose();
            RenderContext.mulPose(Axis.YP.rotationDegrees((float) yaw));
            RenderContext.mulPose(Axis.XP.rotationDegrees((float) (90 - pitch)));

            RenderContext.pushPose();
            RenderContext.scale(1F, (float) length, 1F);
            RenderContext.translate(0F, -0.5F, 0F);
            int color = lightenColor(anchor.getFluidType().getColor(), 0.25D);
            RenderContext.setColor(((color >> 16) & 0xff) / 255F, ((color >> 8) & 0xff) / 255F, (color & 0xff) / 255F, 1F);
            ResourceManager.pipe_anchor.renderPart("Pipe");
            RenderContext.setColor(1F, 1F, 1F, 1F);
            RenderContext.popPose();

            RenderContext.pushPose();
            RenderContext.translate(0F, (float) (length / 2D - 1.5D), 0F);
            ResourceManager.pipe_anchor.renderPart("Ring");
            RenderContext.popPose();

            RenderContext.popPose();
        }
    }

    /** The end at the smaller x, then y, then z draws the pipe; equal points draw nothing (RenderPipeAnchor.java:105-114). */
    public static boolean isDominant(Vec3 first, Vec3 second) {
        if(first.x < second.x) return true;
        if(first.x > second.x) return false;
        if(first.y < second.y) return true;
        if(first.y > second.y) return false;
        return first.z < second.z;
    }

    /** ColorUtil.lightenColor: each channel moves the given share towards white. */
    public static int lightenColor(int hex, double percent) {
        int r = (hex >> 16) & 0xff, g = (hex >> 8) & 0xff, b = hex & 0xff;
        r = (int) (r + (255 - r) * percent);
        g = (int) (g + (255 - g) * percent);
        b = (int) (b + (255 - b) * percent);
        return (r << 16) | (g << 8) | b;
    }

    // A pipe reaches up to ten blocks past the anchor (TileEntityPipelineBase.java:204-213)
    @Override public AABB getRenderBoundingBox(PipeAnchorBlockEntity be) { return AABB.INFINITE; }
    @Override public boolean shouldRenderOffScreen(PipeAnchorBlockEntity be) { return true; }

    @Override
    public Item[] getItemsForRenderer() {
        return new Item[] {NtmBlocks.PIPE_ANCHOR.asItem()};
    }

    @Override
    public BlockEntityWithoutLevelRenderer getRenderer() {
        return new ItemRenderBase() {
            @Override
            public void renderInventory(ItemStack stack, MultiBufferSource buffer) {
                RenderContext.translate(0F, -3.5F, 0F);
                RenderContext.scale(10F, 10F, 10F);
            }

            @Override
            public void renderCommon(ItemStack stack, MultiBufferSource buffer) {
                bindTexture(ResourceManager.PIPE_ANCHOR_TEX);
                ResourceManager.pipe_anchor.renderPart("Anchor");
            }
        };
    }
}
