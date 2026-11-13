package com.hbm.render.util;

import com.hbm.blocks.network.ConveyorBaseBlock;
import com.hbm.items.tools.ConveyorWandItem;
import com.hbm.util.TagsUtil;
import com.hbm.wiaj.WorldInAJar;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import net.minecraft.client.Camera;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.renderer.Sheets;
import net.minecraft.client.renderer.LightTexture;
import net.minecraft.client.renderer.texture.OverlayTexture;
import net.minecraft.client.resources.model.BakedModel;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.util.RandomSource;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.block.RenderShape;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.HitResult;
import net.minecraft.world.phys.Vec3;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.api.distmarker.OnlyIn;
import net.neoforged.neoforge.client.model.data.ModelData;

/**
 * The conveyor wand's route preview (original ItemConveyorWand.java:249-308 and RenderOverhead.java:398-447): while a
 * start point is stored, the route to the block under the crosshair is rebuilt into a world-in-a-jar whenever the aimed
 * block, the aimed face or the player's yaw (by 15 degrees or more) changes, and drawn full-bright, cyan when it can be
 * built and red when not.
 */
@OnlyIn(Dist.CLIENT)
public final class ConveyorWandPreview {

    private static WorldInAJar jar;
    private static BlockPos origin;
    private static boolean success;

    private static BlockPos lastPos;
    private static Direction lastSide;
    private static float lastYaw;

    private ConveyorWandPreview() { }

    public static void clear() {
        jar = null;
        origin = null;
        lastPos = null;
    }

    public static void update(ItemStack stack, Player player) {

        if(!ConveyorWandItem.hasStart(stack)) {
            clear();
            return;
        }

        HitResult hit = Minecraft.getInstance().hitResult;
        if(!(hit instanceof BlockHitResult blockHit) || hit.getType() != HitResult.Type.BLOCK) {
            clear();
            return;
        }

        BlockPos pos = blockHit.getBlockPos();
        Direction side = ConveyorWandItem.snapSide(player.level(), pos, blockHit.getDirection(), true);

        if(lastPos != null && pos.equals(lastPos) && side == lastSide && Math.abs(lastYaw - player.getYRot()) < 15) return;
        lastPos = pos;
        lastSide = side;
        lastYaw = player.getYRot();

        CompoundTag tag = TagsUtil.getCustomData(stack);
        BlockPos start = new BlockPos(tag.getInt("x"), tag.getInt("y"), tag.getInt("z"));
        Direction startSide = Direction.from3DDataValue(tag.getInt("side"));
        int count = tag.getInt("count");

        ConveyorWandItem.Route route = ConveyorWandItem.construct(player.level(), ConveyorWandItem.getType(stack), player, start, startSide, pos, side, count);

        if(route.placements().isEmpty()) {
            jar = null;
            origin = null;
            return;
        }

        // the jar spans the placed blocks with one block of margin, so lifts and chutes at the edge see air neighbours
        int minX = Integer.MAX_VALUE, minY = Integer.MAX_VALUE, minZ = Integer.MAX_VALUE;
        int maxX = Integer.MIN_VALUE, maxY = Integer.MIN_VALUE, maxZ = Integer.MIN_VALUE;
        for(ConveyorWandItem.Placement placement : route.placements()) {
            BlockPos at = placement.pos();
            minX = Math.min(minX, at.getX()); minY = Math.min(minY, at.getY()); minZ = Math.min(minZ, at.getZ());
            maxX = Math.max(maxX, at.getX()); maxY = Math.max(maxY, at.getY()); maxZ = Math.max(maxZ, at.getZ());
        }
        BlockPos min = new BlockPos(minX - 1, minY - 1, minZ - 1);
        WorldInAJar preview = new WorldInAJar(maxX - minX + 3, maxY - minY + 3, maxZ - minZ + 3);

        for(ConveyorWandItem.Placement placement : route.placements()) {
            BlockPos at = placement.pos().subtract(min);
            preview.setBlock(at.getX(), at.getY(), at.getZ(), placement.stateAt(player.level(), placement.pos()));
        }

        // lifts and chutes take their pieces from their neighbours, which in the preview are the other route blocks
        for(ConveyorWandItem.Placement placement : route.placements()) {
            BlockPos at = placement.pos().subtract(min);
            if(preview.getBlock(at.getX(), at.getY(), at.getZ()).getBlock() instanceof ConveyorBaseBlock) {
                preview.setBlock(at.getX(), at.getY(), at.getZ(), placement.stateAt(preview, at));
            }
        }

        jar = preview;
        origin = min;
        success = route.result() > 0;
    }

    public static void render(PoseStack poseStack, Camera camera) {

        if(jar == null || origin == null) return;

        Minecraft mc = Minecraft.getInstance();
        if(mc.player == null || !(mc.player.getMainHandItem().getItem() instanceof ConveyorWandItem) || !ConveyorWandItem.hasStart(mc.player.getMainHandItem())) {
            clear();
            return;
        }

        MultiBufferSource.BufferSource buffers = mc.renderBuffers().bufferSource();
        RenderType type = Sheets.cutoutBlockSheet();
        VertexConsumer tinted = success ? new TintedConsumer(buffers.getBuffer(type), 0, 255, 255) : new TintedConsumer(buffers.getBuffer(type), 255, 0, 0);
        Vec3 cam = camera.getPosition();

        poseStack.pushPose();
        poseStack.translate(origin.getX() - cam.x, origin.getY() - cam.y, origin.getZ() - cam.z);

        for(int ix = 0; ix < jar.sizeX; ix++) {
            for(int iy = 0; iy < jar.sizeY; iy++) {
                for(int iz = 0; iz < jar.sizeZ; iz++) {
                    BlockState state = jar.getBlock(ix, iy, iz);
                    if(state.isAir() || state.getRenderShape() != RenderShape.MODEL) continue;

                    poseStack.pushPose();
                    poseStack.translate(ix, iy, iz);
                    BakedModel model = mc.getBlockRenderer().getBlockModel(state);
                    // the model's quads are split by its own render types; all of them go into the one tinted buffer
                    for(RenderType modelType : model.getRenderTypes(state, RandomSource.create(42L), ModelData.EMPTY)) {
                        mc.getBlockRenderer().getModelRenderer().renderModel(poseStack.last(), tinted, state, model,
                                1F, 1F, 1F, LightTexture.FULL_BRIGHT, OverlayTexture.NO_OVERLAY, ModelData.EMPTY, modelType);
                    }
                    poseStack.popPose();
                }
            }
        }

        poseStack.popPose();
        buffers.endBatch(type);
    }

    /** Replaces every vertex colour, as the original's glColor over a tessellator with its colour disabled. */
    private record TintedConsumer(VertexConsumer delegate, int r, int g, int b) implements VertexConsumer {

        @Override
        public VertexConsumer addVertex(float x, float y, float z) {
            this.delegate.addVertex(x, y, z);
            return this;
        }

        @Override
        public VertexConsumer setColor(int red, int green, int blue, int alpha) {
            this.delegate.setColor(this.r, this.g, this.b, 255);
            return this;
        }

        @Override
        public VertexConsumer setUv(float u, float v) {
            this.delegate.setUv(u, v);
            return this;
        }

        @Override
        public VertexConsumer setUv1(int u, int v) {
            this.delegate.setUv1(u, v);
            return this;
        }

        @Override
        public VertexConsumer setUv2(int u, int v) {
            this.delegate.setUv2(u, v);
            return this;
        }

        @Override
        public VertexConsumer setNormal(float x, float y, float z) {
            this.delegate.setNormal(x, y, z);
            return this;
        }
    }
}
