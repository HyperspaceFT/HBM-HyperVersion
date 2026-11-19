package com.hbm.inventory.screens;

import com.hbm.blockentity.machine.MachineCentrifugeBlockEntity;
import com.hbm.inventory.menus.MachineCentrifugeMenu;
import com.hbm.main.NuclearTechMod;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.player.Inventory;

public class MachineCentrifugeScreen extends InfoScreen<MachineCentrifugeMenu> {

    private static final ResourceLocation TEXTURE = NuclearTechMod.withDefaultNamespace("textures/gui/gui_centrifuge.png");

    private final MachineCentrifugeBlockEntity be;

    public MachineCentrifugeScreen(MachineCentrifugeMenu menu, Inventory inventory, Component title) {
        super(menu, inventory, title);
        this.be = menu.be;
        this.imageWidth = 182;
        this.imageHeight = 189;
    }

    @Override
    public void render(GuiGraphics guiGraphics, int mouseX, int mouseY, float partialTicks) {
        super.render(guiGraphics, mouseX, mouseY, partialTicks);
        this.drawElectricityInfo(guiGraphics, mouseX, mouseY, this.leftPos + 8, this.topPos + 18, 16, 37, this.be.getPower(), this.be.getMaxPower());
        this.renderTooltip(guiGraphics, mouseX, mouseY);
    }

    @Override
    protected void renderLabels(GuiGraphics guiGraphics, int mouseX, int mouseY) {
        // Original GUIMachineCentrifuge.java:43-47 on the same texture: the name in white, centred at x 109 over the machine panel, y 6
        guiGraphics.drawString(this.font, this.title, 109 - this.font.width(this.title) / 2, 6, 0xffffff, false);
        guiGraphics.drawString(this.font, this.playerInventoryTitle, 11, this.imageHeight - 96 + 2, 4210752, false);
    }

    @Override
    protected void renderBg(GuiGraphics guiGraphics, float partialTicks, int mouseX, int mouseY) {
        guiGraphics.blit(TEXTURE, this.leftPos, this.topPos, 0, 0, this.imageWidth, this.imageHeight);

        if(this.be.hasPower()) {
            int power = this.be.getPowerRemainingScaled(37);
            guiGraphics.blit(TEXTURE, this.leftPos + 8, this.topPos + 55 - power, 182, 37 - power, 16, power);
        }

        if(this.be.isProcessing()) {
            int progress = this.be.getCentrifugeProgressScaled(145);
            for(int i = 0; i < 4; i++) {
                int piece = Math.min(progress, 36);
                if(piece > 0) {
                    guiGraphics.blit(TEXTURE, this.leftPos + 72 + i * 20, this.topPos + 57 - piece, 182, 73 - piece, 12, piece);
                }
                progress -= piece;
            }
        }
    }
}
