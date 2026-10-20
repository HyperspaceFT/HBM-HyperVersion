package com.hbm.inventory.screens;

import com.hbm.blockentity.machine.rbmk.RBMKHeaterBlockEntity;
import com.hbm.inventory.menus.RBMKHeaterMenu;
import com.hbm.main.NuclearTechMod;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.player.Inventory;

/** Original GUIRBMKHeater: the input and output tanks and the identifier slot. */
public class RBMKHeaterScreen extends InfoScreen<RBMKHeaterMenu> {

    private static final ResourceLocation TEXTURE = NuclearTechMod.withDefaultNamespace("textures/gui/reactors/gui_rbmk_heater.png");

    private final RBMKHeaterBlockEntity be;

    public RBMKHeaterScreen(RBMKHeaterMenu menu, Inventory playerInventory, Component title) {
        super(menu, playerInventory, title);

        this.be = menu.be;

        this.imageWidth = 176;
        this.imageHeight = 186;
    }

    @Override
    public void render(GuiGraphics guiGraphics, int mouseX, int mouseY, float partialTicks) {
        super.render(guiGraphics, mouseX, mouseY, partialTicks);

        be.feed.renderTankTooltip(guiGraphics, mouseX, mouseY, this.leftPos + 68, this.topPos + 24, 16, 58);
        be.steam.renderTankTooltip(guiGraphics, mouseX, mouseY, this.leftPos + 126, this.topPos + 24, 16, 58);

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

        be.feed.renderTank(this.leftPos + 68, this.topPos + 82, 0, 14, 58);
        be.steam.renderTank(this.leftPos + 126, this.topPos + 82, 0, 14, 58);

        // blit binds the GUI texture again after the fluid textures (the original rebinds it here).
        guiGraphics.blit(TEXTURE, this.leftPos + 72, this.topPos + 72, 176, 0, 10, 10);
        guiGraphics.blit(TEXTURE, this.leftPos + 130, this.topPos + 72, 186, 0, 10, 10);
    }
}
