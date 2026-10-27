package com.hbm.render.blockentity;

import com.hbm.blockentity.machine.FoundryBasinBlockEntity;
import com.hbm.blockentity.machine.FoundryCastingBlockEntity;
import com.hbm.blockentity.machine.FoundryChannelBlockEntity;
import com.hbm.blockentity.machine.FoundryTankBlockEntity;
import com.hbm.blocks.NtmBlocks;
import com.hbm.blocks.machine.FoundryChannelBlock;
import com.hbm.main.ResourceManager;
import com.hbm.render.NtmRenderTypes;
import com.hbm.render.util.RenderContext;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import com.mojang.math.Axis;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.LightTexture;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.renderer.block.model.BakedQuad;
import net.minecraft.client.renderer.blockentity.BlockEntityRenderer;
import net.minecraft.client.renderer.entity.ItemRenderer;
import net.minecraft.client.renderer.texture.OverlayTexture;
import net.minecraft.client.renderer.texture.TextureAtlasSprite;
import net.minecraft.client.resources.model.BakedModel;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.util.RandomSource;
import net.minecraft.world.inventory.InventoryMenu;
import net.minecraft.world.item.BlockItem;
import net.minecraft.world.item.ItemDisplayContext;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;

import java.util.List;

/**
 * Molten metal for foundry channels and tanks (upstream drew it in the RenderFoundryChannel/RenderFoundryTank block renderers) and
 * the mold, cast and molten metal of foundry_mold and foundry_basin (upstream RenderFoundry). The block bodies are static models.
 * The metal is lava_gray tinted with the material's molten colour, full-bright and double-sided.
 */
public class RenderFoundry extends BlockEntityRendererNT<BlockEntity> {

    /** Additive white layer over the mold's metal, upstream's alpha 0.3 with GL_SRC_ALPHA, GL_ONE. */
    private static final int MOLD_OVERLAY_COLOR = (76 << 24) | 0xFFFFFF;
    /** Upstream drawBlock's white at alpha 0.3 for block casts. */
    private static final int BLOCK_CAST_COLOR = (76 << 24) | 0xFFFFFF;

    @Override public BlockEntityRenderer<BlockEntity> create(Context context) { return new RenderFoundry(); }

    @Override
    public void render(BlockEntity be, MultiBufferSource buffer, float partialTicks) {
        if(be instanceof FoundryChannelBlockEntity channel) this.renderChannel(channel, buffer);
        else if(be instanceof FoundryTankBlockEntity tank) this.renderTank(tank, buffer);
        else if(be instanceof FoundryCastingBlockEntity mold) this.renderMold(mold, buffer);
    }

    /** Upstream RenderFoundryChannel.renderWorldBlock: centre surface plus the surface and open end of every connected arm. */
    private void renderChannel(FoundryChannelBlockEntity channel, MultiBufferSource buffer) {
        if(channel.amount <= 0 || channel.type == null) return;

        BlockState state = channel.getBlockState();
        if(!(state.getBlock() instanceof FoundryChannelBlock)) return;

        float bottom = 0.125F;
        float top = bottom + channel.amount * 0.25F / channel.getCapacity();
        int color = brightenedColor(channel.type.moltenColor);
        VertexConsumer buf = buffer.getBuffer(RenderType.entityCutoutNoCull(ResourceManager.FOUNDRY_LAVA_TEX));
        PoseStack.Pose pose = RenderContext.poseStack().last();

        horizontal(buf, pose, color, 0.375F, 0.625F, 0.375F, 0.625F, top);

        if(state.getValue(FoundryChannelBlock.EAST)) {
            horizontal(buf, pose, color, 0.625F, 1F, 0.3125F, 0.6875F, top);
            verticalX(buf, pose, color, 1F, 0.3125F, 0.6875F, bottom, top, 1F);
        }
        if(state.getValue(FoundryChannelBlock.WEST)) {
            horizontal(buf, pose, color, 0F, 0.375F, 0.3125F, 0.6875F, top);
            verticalX(buf, pose, color, 0F, 0.3125F, 0.6875F, bottom, top, -1F);
        }
        if(state.getValue(FoundryChannelBlock.SOUTH)) {
            horizontal(buf, pose, color, 0.3125F, 0.6875F, 0.625F, 1F, top);
            verticalZ(buf, pose, color, 1F, 0.3125F, 0.6875F, bottom, top, 1F);
        }
        if(state.getValue(FoundryChannelBlock.NORTH)) {
            horizontal(buf, pose, color, 0.3125F, 0.6875F, 0F, 0.375F, top);
            verticalZ(buf, pose, color, 0F, 0.3125F, 0.6875F, bottom, top, -1F);
        }
    }

    /**
     * Upstream RenderFoundryTank.renderWorldBlock: a full-width surface whose range grows by 1/8 for a tank above and below, and the
     * metal's side faces towards connected tanks.
     */
    private void renderTank(FoundryTankBlockEntity tank, MultiBufferSource buffer) {
        if(tank.amount <= 0 || tank.type == null) return;

        Level level = tank.getLevel();
        if(level == null) return;
        BlockPos pos = tank.getBlockPos();

        boolean conPosX = isTank(level, pos.east());
        boolean conNegX = isTank(level, pos.west());
        boolean conPosZ = isTank(level, pos.south());
        boolean conNegZ = isTank(level, pos.north());
        boolean conPosY = isTank(level, pos.above());
        boolean conNegY = isTank(level, pos.below());

        float max = 0.75F + (conNegY ? 0.125F : 0F) + (conPosY ? 0.125F : 0F);
        float bottom = conNegY ? 0F : 0.125F;
        float top = bottom + tank.amount * max / tank.getCapacity();
        int color = brightenedColor(tank.type.moltenColor);
        VertexConsumer buf = buffer.getBuffer(RenderType.entityCutoutNoCull(ResourceManager.FOUNDRY_LAVA_TEX));
        PoseStack.Pose pose = RenderContext.poseStack().last();

        horizontal(buf, pose, color, 0F, 1F, 0F, 1F, top);
        if(conPosX) verticalX(buf, pose, color, 1F, 0F, 1F, bottom, top, 1F);
        if(conNegX) verticalX(buf, pose, color, 0F, 0F, 1F, bottom, top, -1F);
        if(conPosZ) verticalZ(buf, pose, color, 1F, 0F, 1F, bottom, top, 1F);
        if(conNegZ) verticalZ(buf, pose, color, 0F, 0F, 1F, bottom, top, -1F);
    }

    private static boolean isTank(Level level, BlockPos pos) {
        return level.getBlockState(pos).is(NtmBlocks.FOUNDRY_TANK.get());
    }

    /**
     * Upstream RenderFoundry with the bounds of TileEntityFoundryMold and TileEntityFoundryBasin (0.125-0.875, mold at 0.13, cast at
     * 0.25 / 0.875, metal at 0.125 + amount * 0.25 / capacity for the mold, 0.75 for the basin). Block casts are drawn as the block's
     * translucent top face at the cast height (upstream drawBlock), other casts as flat items.
     */
    private void renderMold(FoundryCastingBlockEntity mold, MultiBufferSource buffer) {
        boolean basin = mold instanceof FoundryBasinBlockEntity;
        float outHeight = basin ? 0.875F : 0.25F;
        float levelFactor = basin ? 0.75F : 0.25F;

        ItemStack moldItem = mold.getItem(0);
        if(!moldItem.isEmpty()) drawItem(moldItem, 0.13F, buffer);

        ItemStack out = mold.getItem(1);
        if(!out.isEmpty()) {
            if(out.getItem() instanceof BlockItem blockItem) drawBlock(blockItem, outHeight, buffer);
            else drawItem(out, outHeight, buffer);
        }

        int capacity = mold.getCapacity();
        if(mold.amount <= 0 || mold.type == null || capacity <= 0) return;

        float top = 0.125F + mold.amount * levelFactor / capacity;
        PoseStack.Pose pose = RenderContext.poseStack().last();

        // the mold uses the plain molten colour, unlike the channel and tank
        VertexConsumer buf = buffer.getBuffer(RenderType.entityCutoutNoCull(ResourceManager.FOUNDRY_LAVA_TEX));
        horizontal(buf, pose, 0xFF000000 | (mold.type.moltenColor & 0xFFFFFF), 0.125F, 0.875F, 0.125F, 0.875F, top);

        VertexConsumer glow = buffer.getBuffer(NtmRenderTypes.entityAdditive(ResourceManager.FOUNDRY_LAVA_TEX));
        horizontal(glow, pose, MOLD_OVERLAY_COLOR, 0.125F, 0.875F, 0.125F, 0.875F, top);
    }

    /** Upstream drawItem: the item lying flat, scaled to 12/16 of the block and centred. */
    private static void drawItem(ItemStack stack, float height, MultiBufferSource buffer) {
        ItemRenderer renderer = Minecraft.getInstance().getItemRenderer();
        BakedModel model = renderer.getModel(stack, null, null, 0);

        RenderContext.pushPose(); {
            RenderContext.translate(0.5F, height, 0.5F);
            RenderContext.mulPose(Axis.XP.rotationDegrees(-90F));
            RenderContext.scale(0.75F, 0.75F, 0.75F);
            renderer.render(stack, ItemDisplayContext.FIXED, false, RenderContext.poseStack(), buffer, RenderContext.light(), RenderContext.overlay(), model);
        } RenderContext.popPose();
    }

    /** Upstream drawBlock: the block's top-face texture as one quad over the cast area, white at alpha 0.3, world-lit. */
    private static void drawBlock(BlockItem item, float height, MultiBufferSource buffer) {
        BlockState state = item.getBlock().defaultBlockState();
        BakedModel model = Minecraft.getInstance().getBlockRenderer().getBlockModel(state);
        List<BakedQuad> quads = model.getQuads(state, Direction.UP, RandomSource.create(42L));
        TextureAtlasSprite sprite = quads.isEmpty() ? model.getParticleIcon() : quads.get(0).getSprite();

        VertexConsumer buf = buffer.getBuffer(RenderType.entityTranslucent(InventoryMenu.BLOCK_ATLAS));
        PoseStack.Pose pose = RenderContext.poseStack().last();
        int light = RenderContext.light();
        blockVertex(buf, pose, 0.125F, height, 0.125F, sprite.getU0(), sprite.getV1(), light);
        blockVertex(buf, pose, 0.125F, height, 0.875F, sprite.getU1(), sprite.getV1(), light);
        blockVertex(buf, pose, 0.875F, height, 0.875F, sprite.getU1(), sprite.getV0(), light);
        blockVertex(buf, pose, 0.875F, height, 0.125F, sprite.getU0(), sprite.getV0(), light);
    }

    private static void blockVertex(VertexConsumer buf, PoseStack.Pose pose, float x, float y, float z, float u, float v, int light) {
        buf.addVertex(pose, x, y, z).setColor(BLOCK_CAST_COLOR).setUv(u, v).setOverlay(OverlayTexture.NO_OVERLAY).setLight(light).setNormal(pose, 0F, 1F, 0F);
    }

    /**
     * Upstream channel and tank colour: java.awt.Color.brighter() (factor 0.7; components 1-2 become 3, black becomes 3, 3, 3), then
     * every component moved 30% towards white. Returns opaque ARGB.
     */
    public static int brightenedColor(int hex) {
        int r = hex >> 16 & 255;
        int g = hex >> 8 & 255;
        int b = hex & 255;

        if(r == 0 && g == 0 && b == 0) {
            r = g = b = 3;
        } else {
            r = brighter(r);
            g = brighter(g);
            b = brighter(b);
        }

        r = (int) (255D - (255D - r) * 0.7D);
        g = (int) (255D - (255D - g) * 0.7D);
        b = (int) (255D - (255D - b) * 0.7D);

        return 0xFF000000 | r << 16 | g << 8 | b;
    }

    private static int brighter(int c) {
        if(c > 0 && c < 3) c = 3;
        return Math.min((int) (c / 0.7D), 255);
    }

    private static void horizontal(VertexConsumer buf, PoseStack.Pose pose, int color, float x0, float x1, float z0, float z1, float y) {
        vertex(buf, pose, color, x0, y, z0, x0, z0, 0F, 1F, 0F);
        vertex(buf, pose, color, x0, y, z1, x0, z1, 0F, 1F, 0F);
        vertex(buf, pose, color, x1, y, z1, x1, z1, 0F, 1F, 0F);
        vertex(buf, pose, color, x1, y, z0, x1, z0, 0F, 1F, 0F);
    }

    private static void verticalX(VertexConsumer buf, PoseStack.Pose pose, int color, float x, float z0, float z1, float y0, float y1, float nx) {
        vertex(buf, pose, color, x, y0, z0, z0, 1F - y0, nx, 0F, 0F);
        vertex(buf, pose, color, x, y0, z1, z1, 1F - y0, nx, 0F, 0F);
        vertex(buf, pose, color, x, y1, z1, z1, 1F - y1, nx, 0F, 0F);
        vertex(buf, pose, color, x, y1, z0, z0, 1F - y1, nx, 0F, 0F);
    }

    private static void verticalZ(VertexConsumer buf, PoseStack.Pose pose, int color, float z, float x0, float x1, float y0, float y1, float nz) {
        vertex(buf, pose, color, x0, y0, z, x0, 1F - y0, 0F, 0F, nz);
        vertex(buf, pose, color, x1, y0, z, x1, 1F - y0, 0F, 0F, nz);
        vertex(buf, pose, color, x1, y1, z, x1, 1F - y1, 0F, 0F, nz);
        vertex(buf, pose, color, x0, y1, z, x0, 1F - y1, 0F, 0F, nz);
    }

    private static void vertex(VertexConsumer buf, PoseStack.Pose pose, int color, float x, float y, float z, float u, float v, float nx, float ny, float nz) {
        buf.addVertex(pose, x, y, z).setColor(color).setUv(u, v).setOverlay(OverlayTexture.NO_OVERLAY).setLight(LightTexture.FULL_BRIGHT).setNormal(pose, nx, ny, nz);
    }
}
