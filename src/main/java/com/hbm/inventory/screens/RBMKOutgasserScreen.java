package com.hbm.inventory.screens;

import com.hbm.blockentity.machine.rbmk.RBMKOutgasserBlockEntity;
import com.hbm.inventory.menus.RBMKOutgasserMenu;
import com.hbm.main.NuclearTechMod;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.player.Inventory;

/** Original GUIRBMKOutgasser (:14-60): the progress bar and the gas gauge. */
public class RBMKOutgasserScreen extends InfoScreen<RBMKOutgasserMenu> {

    private static final ResourceLocation TEXTURE = NuclearTechMod.withDefaultNamespace("textures/gui/reactors/gui_rbmk_outgasser.png");

    private final RBMKOutgasserBlockEntity be;

    public RBMKOutgasserScreen(RBMKOutgasserMenu menu, Inventory playerInventory, Component title) {
        super(menu, playerInventory, title);

        this.be = menu.be;

        this.imageWidth = 176;
        this.imageHeight = 186;
    }

    @Override
    public void render(GuiGraphics guiGraphics, int mouseX, int mouseY, float partialTicks) {
        super.render(guiGraphics, mouseX, mouseY, partialTicks);

        be.gas.renderTankTooltip(guiGraphics, mouseX, mouseY, this.leftPos + 112, this.topPos + 21, 16, 48);

        this.renderTooltip(guiGraphics, mouseX, mouseY);
    }

    @Override
    protected void renderLabels(GuiGraphics guiGraphics, int mouseX, int mouseY) {
        guiGraphics.drawString(this.font, this.title, this.imageWidth / 2 - this.font.width(this.title) / 2, 6, 4210752, false);
        guiGraphics.drawString(this.font, this.playerInventoryTitle, 8, this.imageHeight - 96 + 2, 4210752, false);
    }

    @Override
    protected void renderBg(GuiGraphics guiGraphics, float partialTicks, int mouseX, int mouseY) {
        guiGraphics.blit(TEXTURE, this.leftPos, this.topPos, 0, 0, this.imageWidth, this.imageHeight);

        int progress = (int) (be.progress * 13 / RBMKOutgasserBlockEntity.DURATION);
        guiGraphics.blit(TEXTURE, this.leftPos + 82, this.topPos + 50, 176, 0, progress, 6);

        int gas = be.gas.getFill() * 42 / be.gas.getMaxFill();
        guiGraphics.blit(TEXTURE, this.leftPos + 115, this.topPos + 66 - gas, 188, 42 - gas, 10, gas);
    }
}
