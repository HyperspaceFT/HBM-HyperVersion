package com.hbm.render.blockentity;

import com.hbm.blockentity.machine.rbmk.RBMKConsoleBlockEntity;
import com.hbm.blockentity.machine.rbmk.RBMKConsoleBlockEntity.RBMKColumn;
import com.hbm.blockentity.machine.rbmk.RBMKConsoleBlockEntity.RBMKScreen;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.NtmBlocks;
import com.hbm.main.ResourceManager;
import com.hbm.render.item.ItemRenderBase;
import com.hbm.render.util.RenderContext;
import com.hbm.util.i18n.I18nUtil;
import com.mojang.blaze3d.vertex.DefaultVertexFormat;
import com.mojang.blaze3d.vertex.VertexConsumer;
import com.mojang.blaze3d.vertex.VertexFormat;
import com.mojang.math.Axis;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.Font;
import net.minecraft.client.renderer.BlockEntityWithoutLevelRenderer;
import net.minecraft.client.renderer.LightTexture;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderStateShard;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.renderer.blockentity.BlockEntityRenderer;
import net.minecraft.core.Direction;
import net.minecraft.util.Mth;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.phys.AABB;
import org.joml.Matrix4f;

/**
 * Original RenderRBMKConsole (:21-182): the console model, one coloured square per watched column with a dot for fuel and control
 * rods, and the six screen texts. The item uses the model as the original ItemRenderLibrary entry (:669-678).
 */
public class RenderRBMKConsole extends BlockEntityRendererNT<RBMKConsoleBlockEntity> implements IBEWLRProvider {

    // Untextured, coloured and lit by the given lightmap value, as the pumpjack's wires; the original disables GL_TEXTURE_2D.
    private static final RenderType COLUMNS = RenderType.create(
            "rbmk_console_columns", DefaultVertexFormat.POSITION_COLOR_LIGHTMAP, VertexFormat.Mode.QUADS, 4096,
            RenderType.CompositeState.builder()
                    .setShaderState(RenderType.RENDERTYPE_TEXT_BACKGROUND_SHADER)
                    .setTextureState(RenderType.NO_TEXTURE)
                    .setLightmapState(RenderType.LIGHTMAP)
                    .setOverlayState(RenderType.OVERLAY)
                    .setCullState(RenderStateShard.NO_CULL)
                    .createCompositeState(false)
    );

    @Override public BlockEntityRenderer<RBMKConsoleBlockEntity> create(Context context) { return new RenderRBMKConsole(); }

    @Override
    public void render(RBMKConsoleBlockEntity be, MultiBufferSource buffer, float partialTicks) {

        RenderContext.translate(0.5F, 0F, 0.5F);

        // Original metadata switch: 2 (north) 90, 4 (west) 180, 3 (south) 270, 5 (east) 0 degrees.
        Direction facing = be.getBlockState().getValue(DummyableBlock.FACING);
        switch(facing) {
            case NORTH -> RenderContext.mulPose(Axis.YP.rotationDegrees(90F));
            case WEST -> RenderContext.mulPose(Axis.YP.rotationDegrees(180F));
            case SOUTH -> RenderContext.mulPose(Axis.YP.rotationDegrees(270F));
            case EAST -> RenderContext.mulPose(Axis.YP.rotationDegrees(0F));
            default -> { }
        }

        RenderContext.translate(0.5F, 0F, 0F);

        bindTexture(ResourceManager.RBMK_CONSOLE_TEX);
        ResourceManager.rbmk_console.renderAll();

        // The original sets brightness 240 for the column squares.
        VertexConsumer consumer = buffer.getBuffer(COLUMNS);
        Matrix4f matrix = RenderContext.poseStack().last().pose();
        int light = LightTexture.FULL_BRIGHT;

        for(int i = 0; i < be.columns.length; i++) {

            RBMKColumn col = be.columns[i];

            if(col == null)
                continue;

            double kx = -0.3725D;
            double ky = -(i / 15) * 0.125 + 3.625;
            double kz = -(i % 15) * 0.125 + 0.125D * 7;

            float r;
            float g;
            float b;

            // The original reads the colour group short with getByte; the values -1 to 4 are the same.
            if(col.data.contains("color") && col.data.getShort("color") >= 0) {
                int rgb = switch(col.data.getShort("color")) {
                    case 0 -> 0xFF0000;
                    case 1 -> 0xFFFF00;
                    case 2 -> 0x008000;
                    case 3 -> 0x0000FF;
                    case 4 -> 0x8000FF;
                    default -> 0xFFFFFF; // the original keeps the previous colour for an unknown group; NEO's rods have none
                };
                r = ((rgb >> 16) & 255) / 255F;
                g = ((rgb >> 8) & 255) / 255F;
                b = (rgb & 255) / 255F;
            } else {
                double heat = col.data.getDouble("heat") / col.data.getDouble("maxHeat");
                double color = 0.65D + (i % 2) * 0.05D;
                r = (float) (color + ((1 - color) * heat));
                g = (float) color;
                b = (float) color;
            }

            if(col.data.getByte("indicator") > 0) {
                r = 1F;
                g = 1F;
                b = 0F;
            }

            drawColumn(consumer, matrix, light, kx, ky, kz, r, g, b);

            switch(col.type) {
                case FUEL, FUEL_SIM -> drawFuel(consumer, matrix, light, kx + 0.01, ky, kz, col.data.getDouble("enrichment"));
                case CONTROL -> drawControl(consumer, matrix, light, kx + 0.01, ky, kz, col.data.getDouble("level"));
                case CONTROL_AUTO -> drawControlAuto(consumer, matrix, light, kx + 0.01, ky, kz, col.data.getDouble("level"));
                default -> { }
            }
        }

        Font font = Minecraft.getInstance().font;
        RenderContext.translate(-0.42F, 3.5F, 1.75F);

        for(int i = 0; i < be.screens.length; i++) {

            RenderContext.pushPose();

            if(i % 2 == 1)
                RenderContext.translate(0F, 0F, 1.75F * -2);

            RenderContext.translate(0F, -0.75F * (i / 2), 0F);

            RBMKScreen screen = be.screens[i];
            String text = screen.display;

            if(text != null && !text.isEmpty()) {

                String[] parts = text.split("=");

                if(parts.length == 2) {
                    text = I18nUtil.resolveKey(parts[0], parts[1]);
                }

                int width = font.width(text);
                int height = font.lineHeight;

                float f3 = Math.min(0.03F, 0.8F / Math.max(width, 1));
                RenderContext.scale(f3, -f3, f3);
                RenderContext.mulPose(Axis.YP.rotationDegrees(90F));

                // The original turns depth writes off for the text; the polygon offset text mode keeps it off the screen face instead.
                font.drawInBatch(text, -width / 2, -height / 2, 0x00ff00, false, RenderContext.poseStack().last().pose(), buffer, Font.DisplayMode.POLYGON_OFFSET, 0, LightTexture.FULL_BRIGHT);
            }

            RenderContext.popPose();
        }
    }

    // Tessellator clamps each channel to 0..255; VertexConsumer does not, so the heat tint (above 1 for an overheated column) is clamped here.
    private static void vertex(VertexConsumer consumer, Matrix4f matrix, int light, double x, double y, double z, float r, float g, float b) {
        consumer.addVertex(matrix, (float) x, (float) y, (float) z).setColor(Mth.clamp(r, 0F, 1F), Mth.clamp(g, 0F, 1F), Mth.clamp(b, 0F, 1F), 1F).setLight(light);
    }

    private static void drawColumn(VertexConsumer consumer, Matrix4f matrix, int light, double x, double y, double z, float r, float g, float b) {

        double width = 0.0625D * 0.75;

        vertex(consumer, matrix, light, x, y + width, z - width, r, g, b);
        vertex(consumer, matrix, light, x, y + width, z + width, r, g, b);
        vertex(consumer, matrix, light, x, y - width, z + width, r, g, b);
        vertex(consumer, matrix, light, x, y - width, z - width, r, g, b);
    }

    private static void drawFuel(VertexConsumer consumer, Matrix4f matrix, int light, double x, double y, double z, double enrichment) {
        drawDot(consumer, matrix, light, x, y, z, 0F, 0.25F + (float) (enrichment * 0.75D), 0F);
    }

    private static void drawControl(VertexConsumer consumer, Matrix4f matrix, int light, double x, double y, double z, double level) {
        drawDot(consumer, matrix, light, x, y, z, (float) level, (float) level, 0F);
    }

    private static void drawControlAuto(VertexConsumer consumer, Matrix4f matrix, int light, double x, double y, double z, double level) {
        drawDot(consumer, matrix, light, x, y, z, (float) level, 0F, (float) level);
    }

    private static void drawDot(VertexConsumer consumer, Matrix4f matrix, int light, double x, double y, double z, float r, float g, float b) {

        double width = 0.03125D;
        double edge = 0.022097D;

        vertex(consumer, matrix, light, x, y + width, z, r, g, b);
        vertex(consumer, matrix, light, x, y + edge, z + edge, r, g, b);
        vertex(consumer, matrix, light, x, y, z + width, r, g, b);
        vertex(consumer, matrix, light, x, y - edge, z + edge, r, g, b);

        vertex(consumer, matrix, light, x, y + edge, z - edge, r, g, b);
        vertex(consumer, matrix, light, x, y + width, z, r, g, b);
        vertex(consumer, matrix, light, x, y - edge, z - edge, r, g, b);
        vertex(consumer, matrix, light, x, y, z - width, r, g, b);

        vertex(consumer, matrix, light, x, y + width, z, r, g, b);
        vertex(consumer, matrix, light, x, y - edge, z + edge, r, g, b);
        vertex(consumer, matrix, light, x, y - width, z, r, g, b);
        vertex(consumer, matrix, light, x, y - edge, z - edge, r, g, b);
    }

    @Override
    public AABB getRenderBoundingBox(RBMKConsoleBlockEntity be) {
        return be.getRenderBoundingBox();
    }

    @Override
    public Item getItemForRenderer() {
        return NtmBlocks.RBMK_CONSOLE.asItem();
    }

    @Override
    public BlockEntityWithoutLevelRenderer getRenderer() {
        return new ItemRenderBase() {
            @Override
            public void renderInventory(ItemStack stack, MultiBufferSource buffer) {
                RenderContext.translate(0F, -3F, 0F);
                RenderContext.scale(2.5F, 2.5F, 2.5F);
            }

            @Override
            public void renderCommon(ItemStack stack, MultiBufferSource buffer) {
                bindTexture(ResourceManager.RBMK_CONSOLE_TEX);
                ResourceManager.rbmk_console.renderAll();
            }
        };
    }
}
