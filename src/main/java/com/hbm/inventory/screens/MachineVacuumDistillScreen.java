package com.hbm.inventory.screens;

import com.hbm.blockentity.machine.oil.MachineVacuumDistillBlockEntity;
import com.hbm.inventory.menus.MachineVacuumDistillMenu;
import com.hbm.main.NuclearTechMod;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.player.Inventory;

public class MachineVacuumDistillScreen extends InfoScreen<MachineVacuumDistillMenu> {

    private static final ResourceLocation TEXTURE = NuclearTechMod.withDefaultNamespace("textures/gui/processing/gui_vacuum_distill.png");

    private final MachineVacuumDistillBlockEntity be;

    public MachineVacuumDistillScreen(MachineVacuumDistillMenu menu, Inventory inventory, Component title) {
        super(menu, inventory, title);
        this.be = menu.be;
        this.imageWidth = 176;
        this.imageHeight = 238;
    }

    @Override
    public void render(GuiGraphics guiGraphics, int mouseX, int mouseY, float partialTicks) {
        super.render(guiGraphics, mouseX, mouseY, partialTicks);

        this.be.tanks[0].renderTankTooltip(guiGraphics, mouseX, mouseY, this.leftPos + 44, this.topPos + 18, 16, 52);
        this.be.tanks[1].renderTankTooltip(guiGraphics, mouseX, mouseY, this.leftPos + 80, this.topPos + 18, 16, 52);
        this.be.tanks[2].renderTankTooltip(guiGraphics, mouseX, mouseY, this.leftPos + 98, this.topPos + 18, 16, 52);
        this.be.tanks[3].renderTankTooltip(guiGraphics, mouseX, mouseY, this.leftPos + 116, this.topPos + 18, 16, 52);
        this.be.tanks[4].renderTankTooltip(guiGraphics, mouseX, mouseY, this.leftPos + 134, this.topPos + 18, 16, 52);

        this.drawElectricityInfo(guiGraphics, mouseX, mouseY, this.leftPos + 26, this.topPos + 18, 16, 52, this.be.power, MachineVacuumDistillBlockEntity.MAX_POWER);
        this.renderTooltip(guiGraphics, mouseX, mouseY);
    }

    @Override
    protected void renderLabels(GuiGraphics guiGraphics, int mouseX, int mouseY) {
        guiGraphics.drawString(this.font, this.title, this.imageWidth / 2 - this.font.width(this.title) / 2, 5, 0xFFFFFF, false);
        guiGraphics.drawString(this.font, this.playerInventoryTitle, 8, this.imageHeight - 96 + 2, 4210752, false);
    }

    @Override
    protected void renderBg(GuiGraphics guiGraphics, float partialTicks, int mouseX, int mouseY) {
        guiGraphics.blit(TEXTURE, this.leftPos, this.topPos, 0, 0, this.imageWidth, this.imageHeight);

        int j = (int) (this.be.power * 54 / MachineVacuumDistillBlockEntity.MAX_POWER);
        guiGraphics.blit(TEXTURE, this.leftPos + 26, this.topPos + 70 - j, 176, 52 - j, 16, j);

        this.be.tanks[0].renderTank(this.leftPos + 44, this.topPos + 70, 0, 16, 52);
        this.be.tanks[1].renderTank(this.leftPos + 80, this.topPos + 70, 0, 16, 52);
        this.be.tanks[2].renderTank(this.leftPos + 98, this.topPos + 70, 0, 16, 52);
        this.be.tanks[3].renderTank(this.leftPos + 116, this.topPos + 70, 0, 16, 52);
        this.be.tanks[4].renderTank(this.leftPos + 134, this.topPos + 70, 0, 16, 52);
    }
}
