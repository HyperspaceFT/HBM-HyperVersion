package com.hbm.inventory.screens;

import com.hbm.blockentity.machine.MachineFurnaceCombinationBlockEntity;
import com.hbm.inventory.menus.MachineFurnaceCombinationMenu;
import com.hbm.main.NuclearTechMod;
import net.minecraft.ChatFormatting;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.player.Inventory;

public class MachineFurnaceCombinationScreen extends InfoScreen<MachineFurnaceCombinationMenu> {

    private static final ResourceLocation TEXTURE = NuclearTechMod.withDefaultNamespace("textures/gui/processing/gui_furnace_combination.png");

    private final MachineFurnaceCombinationBlockEntity be;

    public MachineFurnaceCombinationScreen(MachineFurnaceCombinationMenu menu, Inventory inventory, Component title) {
        super(menu, inventory, title);
        this.be = menu.be;
        this.imageWidth = 176;
        this.imageHeight = 186;
    }

    @Override
    public void render(GuiGraphics guiGraphics, int mouseX, int mouseY, float partialTicks) {
        super.render(guiGraphics, mouseX, mouseY, partialTicks);
        this.be.tank.renderTankTooltip(guiGraphics, mouseX, mouseY, this.leftPos + 118, this.topPos + 18, 16, 52);
        this.drawCustomInfoStat(guiGraphics, mouseX, mouseY, this.leftPos + 44, this.topPos + 36, 39, 7, mouseX, mouseY,
                Component.translatable("container.furnace_combination.progress", String.format("%,d", this.be.progress), String.format("%,d", MachineFurnaceCombinationBlockEntity.PROCESS_TIME)).withStyle(ChatFormatting.YELLOW),
                Component.translatable("container.furnace_combination.process"),
                Component.translatable("container.furnace_combination.blocked"));
        this.drawCustomInfoStat(guiGraphics, mouseX, mouseY, this.leftPos + 44, this.topPos + 45, 39, 7, mouseX, mouseY,
                Component.translatable("container.heaterFirebox.heat", String.format("%,d", this.be.heat), String.format("%,d", MachineFurnaceCombinationBlockEntity.MAX_HEAT)).withStyle(ChatFormatting.YELLOW),
                Component.translatable("container.furnace_combination.placement"),
                Component.translatable("container.furnace_combination.interruption"));
        this.drawCustomInfoStat(guiGraphics, mouseX, mouseY, this.leftPos + 26, this.topPos + 36, 16, 16, mouseX, mouseY,
                Component.translatable("container.furnace_combination.input"),
                Component.translatable("container.furnace_combination.switch"));
        this.drawCustomInfoStat(guiGraphics, mouseX, mouseY, this.leftPos + 136, this.topPos + 18, 16, 16, mouseX, mouseY,
                Component.translatable("container.furnace_combination.container"),
                Component.translatable("container.furnace_combination.container_amount"),
                Component.translatable("container.furnace_combination.container_whole"),
                Component.translatable("container.furnace_combination.container_blocked"));
        this.drawCustomInfoStat(guiGraphics, mouseX, mouseY, this.leftPos + 136, this.topPos + 54, 16, 16, mouseX, mouseY,
                Component.translatable("container.furnace_combination.container_recovery"),
                Component.translatable("container.furnace_combination.container_unload"));
        this.renderTooltip(guiGraphics, mouseX, mouseY);
    }

    @Override
    protected void renderLabels(GuiGraphics guiGraphics, int mouseX, int mouseY) {
        guiGraphics.drawString(this.font, this.title, this.imageWidth / 2 - this.font.width(this.title) / 2, 6, 4210752, false);
        guiGraphics.drawString(this.font, this.playerInventoryTitle, 8, this.imageHeight - 96 + 2, 4210752, false);
    }

    @Override
    protected void renderBg(GuiGraphics guiGraphics, float partialTicks, int mouseX, int mouseY) {
        guiGraphics.blit(TEXTURE, this.leftPos, this.topPos, 0, 0, this.imageWidth, this.imageHeight, 256, 256);
        int progress = this.be.getProgressScaled(38);
        if(progress > 0) guiGraphics.blit(TEXTURE, this.leftPos + 45, this.topPos + 37, 176, 0, progress, 5, 256, 256);
        int heat = this.be.getHeatScaled(37);
        if(heat > 0) guiGraphics.blit(TEXTURE, this.leftPos + 45, this.topPos + 46, 176, 5, heat, 5, 256, 256);
        this.be.tank.renderTank(this.leftPos + 118, this.topPos + 70, 0.0F, 16, 52);
    }
}
