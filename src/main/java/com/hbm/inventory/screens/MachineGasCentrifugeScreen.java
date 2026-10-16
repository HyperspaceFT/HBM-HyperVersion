package com.hbm.inventory.screens;

import com.hbm.blockentity.machine.MachineGasCentrifugeBlockEntity;
import com.hbm.blockentity.machine.MachineGasCentrifugeBlockEntity.PseudoFluidTank;
import com.hbm.inventory.menus.MachineGasCentrifugeMenu;
import com.hbm.main.NuclearTechMod;
import com.hbm.util.i18n.I18nUtil;
import com.mojang.blaze3d.systems.RenderSystem;
import com.mojang.blaze3d.vertex.BufferBuilder;
import com.mojang.blaze3d.vertex.BufferUploader;
import com.mojang.blaze3d.vertex.DefaultVertexFormat;
import com.mojang.blaze3d.vertex.Tesselator;
import com.mojang.blaze3d.vertex.VertexFormat;
import net.minecraft.ChatFormatting;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.renderer.GameRenderer;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.player.Inventory;
import org.joml.Matrix4f;

import java.util.ArrayList;
import java.util.List;

public class MachineGasCentrifugeScreen extends InfoScreen<MachineGasCentrifugeMenu> {

    private static final ResourceLocation TEXTURE = NuclearTechMod.withDefaultNamespace("textures/gui/processing/gui_centrifuge_gas.png");

    private final MachineGasCentrifugeBlockEntity be;

    public MachineGasCentrifugeScreen(MachineGasCentrifugeMenu menu, Inventory inventory, Component title) {
        super(menu, inventory, title);
        this.be = menu.be;
        this.imageWidth = 206;
        this.imageHeight = 204;
    }

    @Override
    public void render(GuiGraphics guiGraphics, int mouseX, int mouseY, float partialTicks) {
        super.render(guiGraphics, mouseX, mouseY, partialTicks);

        MutableComponent inName = this.be.inputTank.getTankType().getName().copy();
        if(this.be.inputTank.getTankType().getIfHighSpeed()) {
            // Red while the speed upgrade required for this stage is missing.
            inName.withStyle(this.be.getProcessingSpeed() > MachineGasCentrifugeBlockEntity.UPGRADED_PROCESSING_SPEED ? ChatFormatting.DARK_RED : ChatFormatting.GOLD);
        }
        MutableComponent outName = this.be.outputTank.getTankType().getName().copy();
        if(this.be.outputTank.getTankType().getIfHighSpeed()) outName.withStyle(ChatFormatting.GOLD);

        this.drawCustomInfoStat(guiGraphics, mouseX, mouseY, this.leftPos + 15, this.topPos + 15, 24, 55, mouseX, mouseY, inName, getFillText(this.be.inputTank));
        this.drawCustomInfoStat(guiGraphics, mouseX, mouseY, this.leftPos + 137, this.topPos + 15, 25, 55, mouseX, mouseY, outName, getFillText(this.be.outputTank));

        this.drawElectricityInfo(guiGraphics, mouseX, mouseY, this.leftPos + 182, this.topPos + 69 - 52, 16, 52, this.be.getPower(), MachineGasCentrifugeBlockEntity.MAX_POWER);

        this.drawCustomInfoStat(guiGraphics, mouseX, mouseY, this.leftPos - 12, this.topPos + 16, 16, 16, this.leftPos - 8, this.topPos + 16 + 16, toComponents(I18nUtil.resolveKeyArray("desc.gui.gasCent.enrichment")));
        this.drawCustomInfoStat(guiGraphics, mouseX, mouseY, this.leftPos - 12, this.topPos + 32, 16, 16, this.leftPos - 8, this.topPos + 32 + 16, toComponents(I18nUtil.resolveKeyArray("desc.gui.gasCent.output")));

        this.renderTooltip(guiGraphics, mouseX, mouseY);
    }

    private static Component getFillText(PseudoFluidTank tank) {
        return Component.literal(tank.getFill() + " / " + tank.getMaxFill() + " mB");
    }

    private static List<Component> toComponents(String[] lines) {
        List<Component> components = new ArrayList<>();
        for(String line : lines) components.add(Component.literal(line));
        return components;
    }

    @Override
    protected void renderLabels(GuiGraphics guiGraphics, int mouseX, int mouseY) {
        guiGraphics.drawString(this.font, this.playerInventoryTitle, 8, this.imageHeight - 96 + 2, 4210752, false);
    }

    @Override
    protected void renderBg(GuiGraphics guiGraphics, float partialTicks, int mouseX, int mouseY) {
        guiGraphics.blit(TEXTURE, this.leftPos, this.topPos, 0, 0, this.imageWidth, this.imageHeight);

        int i = (int) this.be.getPowerRemainingScaled(52);
        guiGraphics.blit(TEXTURE, this.leftPos + 182, this.topPos + 69 - i, 206, 52 - i, 16, i);

        int j = this.be.getCentrifugeProgressScaled(36);
        guiGraphics.blit(TEXTURE, this.leftPos + 70, this.topPos + 35, 206, 52, j, 13);

        this.renderTank(guiGraphics, this.leftPos + 16, this.topPos + 16, 6, 52, this.be.inputTank.getFill(), this.be.inputTank.getMaxFill());
        this.renderTank(guiGraphics, this.leftPos + 32, this.topPos + 16, 6, 52, this.be.inputTank.getFill(), this.be.inputTank.getMaxFill());

        this.renderTank(guiGraphics, this.leftPos + 138, this.topPos + 16, 6, 52, this.be.outputTank.getFill(), this.be.outputTank.getMaxFill());
        this.renderTank(guiGraphics, this.leftPos + 154, this.topPos + 16, 6, 52, this.be.outputTank.getFill(), this.be.outputTank.getMaxFill());

        this.drawInfoPanel(guiGraphics, this.leftPos - 12, this.topPos + 16, 3);
        this.drawInfoPanel(guiGraphics, this.leftPos - 12, this.topPos + 32, 2);
    }

    /**
     * The pseudo tanks are drawn with the texture of the real fluid, untinted (original GUIMachineGasCent.java:256-285).
     * The original quad starts at the top of the gauge and grows downward by fill * height / max; that is kept as is.
     */
    private void renderTank(GuiGraphics guiGraphics, int x, int y, int width, int height, int fluid, int maxFluid) {
        if(maxFluid <= 0) return;
        int i = Math.max(0, Math.min(height, fluid * height / maxFluid));
        if(i <= 0) return;

        float minX = x;
        float maxX = x + width;
        float minY = y;
        float maxY = y + i;

        float minV = 1F;
        float maxV = 1F - i / 16F;
        float minU = 0F;
        float maxU = width / 16F;

        RenderSystem.enableBlend();
        RenderSystem.setShader(GameRenderer::getPositionTexColorShader);
        RenderSystem.setShaderTexture(0, this.be.tank.getTankType().getTexture());

        Matrix4f matrix = guiGraphics.pose().last().pose();
        BufferBuilder buf = Tesselator.getInstance().begin(VertexFormat.Mode.QUADS, DefaultVertexFormat.POSITION_TEX_COLOR);
        buf.addVertex(matrix, minX, maxY, 0F).setUv(minU, maxV).setColor(1F, 1F, 1F, 1F);
        buf.addVertex(matrix, maxX, maxY, 0F).setUv(maxU, maxV).setColor(1F, 1F, 1F, 1F);
        buf.addVertex(matrix, maxX, minY, 0F).setUv(maxU, minV).setColor(1F, 1F, 1F, 1F);
        buf.addVertex(matrix, minX, minY, 0F).setUv(minU, minV).setColor(1F, 1F, 1F, 1F);
        BufferUploader.drawWithShader(buf.buildOrThrow());

        RenderSystem.disableBlend();
    }
}
