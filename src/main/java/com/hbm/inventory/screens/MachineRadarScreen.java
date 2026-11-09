package com.hbm.inventory.screens;

import api.hbm.entity.RadarEntry;
import com.hbm.blockentity.machine.MachineRadarBlockEntity;
import com.hbm.main.NuclearTechMod;
import com.hbm.network.toserver.CompoundTagControl;
import com.hbm.util.BobMathUtil;
import com.hbm.util.i18n.I18nUtil;
import com.mojang.blaze3d.systems.RenderSystem;
import com.mojang.blaze3d.vertex.*;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.client.renderer.GameRenderer;
import net.minecraft.client.resources.sounds.SimpleSoundInstance;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.util.Mth;
import net.minecraft.util.RandomSource;
import net.neoforged.neoforge.network.PacketDistributor;
import org.joml.Matrix4f;
import org.joml.Vector3f;

import java.util.ArrayList;
import java.util.List;

public class MachineRadarScreen extends Screen {

    public static final ResourceLocation TEXTURE = NuclearTechMod.withDefaultNamespace("textures/gui/machine/gui_radar_nt.png");

    protected MachineRadarBlockEntity be;
    protected int imageWidth = 216;
    protected int imageHeight = 234;
    protected int leftPos;
    protected int topPos;

    public int lastMouseX;
    public int lastMouseY;

    public MachineRadarScreen(MachineRadarBlockEntity be) {
        super(Component.translatable("container.radar_screen"));

        this.be = be;
    }

    @Override
    protected void init() {

        this.leftPos = (this.width - this.imageWidth) / 2;
        this.topPos = (this.height - this.imageHeight) / 2;
    }

    @Override
    public boolean mouseClicked(double mouseX, double mouseY, int button) {

        String cmd = null;

        if(this.isHovered(mouseX, mouseY, -10, 88, 8, 8)) cmd = "missiles";
        if(this.isHovered(mouseX, mouseY, -10, 98, 8, 8)) cmd = "shells";
        if(this.isHovered(mouseX, mouseY, -10, 108, 8, 8)) cmd = "players";
        if(this.isHovered(mouseX, mouseY, -10, 118, 8, 8)) cmd = "smart";
        if(this.isHovered(mouseX, mouseY, -10, 128, 8, 8)) cmd = "red";
        if(this.isHovered(mouseX, mouseY, -10, 138, 8, 8)) cmd = "map";
        if(this.isHovered(mouseX, mouseY, -10, 158, 8, 8)) cmd = "gui1";
        if(this.isHovered(mouseX, mouseY, -10, 178, 8, 8)) cmd = "clear";

        if(cmd != null) {
            this.click();
            CompoundTag tag = new CompoundTag();
            tag.putBoolean(cmd, true);
            PacketDistributor.sendToServer(new CompoundTagControl(tag, this.be.getBlockPos()));
        }

        return super.mouseClicked(mouseX, mouseY, button);
    }

    @Override
    public void render(GuiGraphics guiGraphics, int mouseX, int mouseY, float partialTicks) {
        this.renderBackground(guiGraphics, mouseX, mouseY, partialTicks);

        this.lastMouseX = mouseX;
        this.lastMouseY = mouseY;
    }

    @Override
    public void renderBackground(GuiGraphics guiGraphics, int mouseX, int mouseY, float partialTicks) {
        this.renderTransparentBackground(guiGraphics);

        this.renderBg(guiGraphics, partialTicks, mouseX, mouseY);
        this.renderLabels(guiGraphics, mouseX, mouseY);
    }

    protected void renderLabels(GuiGraphics guiGraphics, int mouseX, int mouseY) {

        if(this.isHovered(mouseX, mouseY, 8, 221, 200, 7)) guiGraphics.renderTooltip(this.font, Component.translatable(BobMathUtil.getShortNumber(be.power) + "/" + BobMathUtil.getShortNumber(MachineRadarBlockEntity.maxPower) + I18nUtil.resolveKey("he")), mouseX, mouseY);

        if(this.isHovered(mouseX, mouseY, -10, 88, 8, 8)) this.renderLines(guiGraphics, "radar.detectMissiles", mouseX, mouseY);
        if(this.isHovered(mouseX, mouseY, -10, 98, 8, 8)) this.renderLines(guiGraphics, "radar.detectShells", mouseX, mouseY);
        if(this.isHovered(mouseX, mouseY, -10, 108, 8, 8)) this.renderLines(guiGraphics, "radar.detectPlayers", mouseX, mouseY);
        if(this.isHovered(mouseX, mouseY, -10, 118, 8, 8)) this.renderLines(guiGraphics, "radar.smartMode", mouseX, mouseY);
        if(this.isHovered(mouseX, mouseY, -10, 128, 8, 8)) this.renderLines(guiGraphics, "radar.redMode", mouseX, mouseY);
        if(this.isHovered(mouseX, mouseY, -10, 138, 8, 8)) this.renderLines(guiGraphics, "radar.showMap", mouseX, mouseY);
        if(this.isHovered(mouseX, mouseY, -10, 158, 8, 8)) this.renderLines(guiGraphics, "radar.toggleGui", mouseX, mouseY);
        if(this.isHovered(mouseX, mouseY, -10, 178, 8, 8)) this.renderLines(guiGraphics, "radar.clearMap", mouseX, mouseY);

        // GUIMachineRadarNT.java:95-113: a blip under the cursor shows its name, X / Z and height; otherwise the map shows the world X / Z
        if(!be.entries.isEmpty()) {
            for(RadarEntry m : be.entries) {
                int x = this.leftPos + (int) ((m.pos.getX() - be.getBlockPos().getX()) / ((double) be.getRange() * 2 + 1) * (200D - 8D)) + 108;
                int z = this.topPos + (int) ((m.pos.getZ() - be.getBlockPos().getZ()) / ((double) be.getRange() * 2 + 1) * (200D - 8D)) + 117;

                if(mouseX + 5 > x && mouseX - 4 <= x && mouseY + 5 > z && mouseY - 4 <= z) {
                    List<Component> text = List.of(m.name, Component.literal(m.pos.getX() + " / " + m.pos.getZ()), Component.translatable("radar.altitude", m.pos.getY()));
                    guiGraphics.renderComponentTooltip(this.font, text, x, z);
                    return;
                }
            }
        }

        if(this.isHovered(mouseX, mouseY, 8, 17, 200, 200)) {
            int tX = (int) ((lastMouseX - this.leftPos - 108) * ((double) be.getRange() * 2 + 1) / 192D + be.getBlockPos().getX());
            int tZ = (int) ((lastMouseY - this.topPos - 117) * ((double) be.getRange() * 2 + 1) / 192D + be.getBlockPos().getZ());
            guiGraphics.renderTooltip(this.font, Component.literal(tX + " / " + tZ), lastMouseX, lastMouseY);
        }
    }

    /** Splits the translation at NTM's $ line break, as the original I18nUtil.resolveKeyArray tooltips. */
    protected void renderLines(GuiGraphics guiGraphics, String key, int mouseX, int mouseY) {
        List<Component> lines = new ArrayList<>();
        for(String s : I18nUtil.resolveKeyArray(key)) lines.add(Component.literal(s));
        guiGraphics.renderComponentTooltip(this.font, lines, mouseX, mouseY);
    }

    @SuppressWarnings("DataFlowIssue")
    protected void renderBg(GuiGraphics guiGraphics, float partialTicks, int mouseX, int mouseY) {
        guiGraphics.blit(TEXTURE, this.leftPos, this.topPos, 0, 0, imageWidth, imageHeight);
        guiGraphics.blit(TEXTURE, this.leftPos - 14, this.topPos + 84, 224, 0, 14, 66);
        guiGraphics.blit(TEXTURE, this.leftPos - 14, this.topPos + 154, 224, 66, 14, 36);

        if(be.power > 0) {
            int i = (int) (be.power * 200 / MachineRadarBlockEntity.maxPower);
            guiGraphics.blit(TEXTURE, this.leftPos + 8, this.topPos + 221, 0, 234, i, 16);
        }

        RandomSource random = be.getLevel().random;
        if(be.scanMissiles ^ (be.jammed && random.nextBoolean())) guiGraphics.blit(TEXTURE, this.leftPos - 10, this.topPos + 88, 238, 4, 8, 8);
        if(be.scanShells ^ (be.jammed && random.nextBoolean())) guiGraphics.blit(TEXTURE, this.leftPos - 10, this.topPos + 98, 238, 14, 8, 8);
        if(be.scanPlayers ^ (be.jammed && random.nextBoolean())) guiGraphics.blit(TEXTURE, this.leftPos - 10, this.topPos + 108, 238, 24, 8, 8);
        if(be.smartMode ^ (be.jammed && random.nextBoolean())) guiGraphics.blit(TEXTURE, this.leftPos - 10, this.topPos + 118, 238, 34, 8, 8);
        if(be.redMode ^ (be.jammed && random.nextBoolean())) guiGraphics.blit(TEXTURE, this.leftPos - 10, this.topPos + 128, 238, 44, 8, 8);
        if(be.showMap ^ (be.jammed && random.nextBoolean())) guiGraphics.blit(TEXTURE, this.leftPos - 10, this.topPos + 138, 238, 54, 8, 8);

        if(be.power < MachineRadarBlockEntity.consumption) return;

        if(be.jammed) {
            for(int i = 0; i < 5; i++) {
                for(int j = 0; j < 5; j++) {
                    guiGraphics.blit(TEXTURE, this.leftPos + 8 + i * 40, this.topPos + 17 + j * 40, 216, 118 + random.nextInt(81), 40, 40);
                }
            }
            return;
        }

        if(be.showMap) {
            RenderSystem.setShader(GameRenderer::getPositionColorShader);
            Matrix4f matrix = guiGraphics.pose().last().pose();
            BufferBuilder buffer = Tesselator.getInstance().begin(VertexFormat.Mode.QUADS, DefaultVertexFormat.POSITION_COLOR);
            for(int i = 0; i < 40_000; i++) {
                int iX = i % 200;
                int iZ = i / 200;
                byte b = be.map[i];
                if(b > 0) {
                    int color = 0xFF000000 | ((b - 50) * 255 / 78) << 8;
                    buffer.addVertex(matrix, this.leftPos + 8 + iX,	this.topPos + 18 + iZ,	1F).setColor(color);
                    buffer.addVertex(matrix, this.leftPos + 9 + iX,	this.topPos + 18 + iZ,	1F).setColor(color);
                    buffer.addVertex(matrix, this.leftPos + 9 + iX,	this.topPos + 17 + iZ,	1F).setColor(color);
                    buffer.addVertex(matrix, this.leftPos + 8 + iX,	this.topPos + 17 + iZ,	1F).setColor(color);
                }
            }
            // an all-zero map adds no vertex; the 1.7.10 Tessellator drew nothing, buildOrThrow would throw
            MeshData data = buffer.build();
            if(data != null) BufferUploader.drawWithShader(data);
        }

        Vector3f tr = new Vector3f(100, 0, 0);
        Vector3f tl = new Vector3f(100, 0, 0);
        Vector3f bl = new Vector3f(0, -5, 0);
        float rot = (float) -Math.toRadians(Mth.lerp(partialTicks + 180F, be.prevRotation, be.rotation));
        tr.rotateZ(rot);
        tl.rotateZ(rot + 0.25F);
        bl.rotateZ(rot);

        RenderSystem.setShader(GameRenderer::getPositionColorShader);
        Matrix4f matrix = guiGraphics.pose().last().pose();
        BufferBuilder buffer = Tesselator.getInstance().begin(VertexFormat.Mode.QUADS, DefaultVertexFormat.POSITION_COLOR);
        RenderSystem.enableBlend();
        buffer.addVertex(matrix, this.leftPos + 108,        	this.topPos + 117,		    2F).setColor(0F, 1F, 0F, 0F);
        buffer.addVertex(matrix, this.leftPos + 108 + tr.x,	this.topPos + 117 + tr.y,	2F).setColor(0F, 1F, 0F, 1F);
        buffer.addVertex(matrix, this.leftPos + 108 + tl.x,	this.topPos + 117 + tl.y,	2F).setColor(0F, 1F, 0F, 0F);
        buffer.addVertex(matrix, this.leftPos + 108 + bl.x,	this.topPos + 117 + bl.y,	2F).setColor(0F, 1F, 0F, 0F);
        RenderSystem.disableBlend();
        BufferUploader.drawWithShader(buffer.buildOrThrow());

        if(!be.entries.isEmpty()) {
            for(RadarEntry m : be.entries) {
                float x = (m.pos.getX() - be.getBlockPos().getX()) / ((float) be.getRange() * 2 + 1) * (200F - 8F) - 4F;
                float z = (m.pos.getZ() - be.getBlockPos().getZ()) / ((float) be.getRange() * 2 + 1) * (200F - 8F) - 4F;
                int t = m.blipLevel;
                this.blitFloat(TEXTURE, guiGraphics, this.leftPos + 108 + x, this.topPos + 117 + z, 216, 8 * t, 8, 8);
            }
        }
    }

    public void blitFloat(ResourceLocation texture, GuiGraphics guiGraphics, float x, float y, int sourceX, int sourceY, int sizeX, int sizeY) {
        float f = 0.00390625F;
        float f1 = 0.00390625F;
        RenderSystem.setShaderTexture(0, texture);
        RenderSystem.setShader(GameRenderer::getPositionTexShader);
        Matrix4f matrix = guiGraphics.pose().last().pose();
        BufferBuilder buffer = Tesselator.getInstance().begin(VertexFormat.Mode.QUADS, DefaultVertexFormat.POSITION_TEX);
        buffer.addVertex(matrix, x,            y + sizeY, 1F).setUv((sourceX + 0) * f,     (sourceY + sizeY) * f1);
        buffer.addVertex(matrix, x + sizeX, y + sizeY, 1F).setUv((sourceX + sizeX) * f, (sourceY + sizeY) * f1);
        buffer.addVertex(matrix, x + sizeX,    y,         1F).setUv((sourceX + sizeX) * f, (sourceY + 0) * f1);
        buffer.addVertex(matrix, x,               y,         1F).setUv((sourceX + 0) * f,     (sourceY + 0) * f1);
        BufferUploader.drawWithShader(buffer.buildOrThrow());
    }

    @Override
    public boolean isPauseScreen() {
        return false;
    }

    protected boolean isHovered(double mouseX, double mouseY, int left, int top, int sizeX, int sizeY) {
        return leftPos + left <= mouseX && leftPos + left + sizeX > mouseX && topPos + top < mouseY && topPos + top + sizeY >= mouseY;
    }

    @SuppressWarnings("DataFlowIssue")
    public void click() {
        this.minecraft.getSoundManager().play(SimpleSoundInstance.forUI(SoundEvents.UI_BUTTON_CLICK, 1.0F));
    }
}
