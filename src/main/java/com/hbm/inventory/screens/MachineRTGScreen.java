package com.hbm.inventory.screens;

import com.hbm.blockentity.machine.MachineRTGBlockEntity;
import com.hbm.inventory.menus.MachineRTGMenu;
import com.hbm.items.machine.RTGPelletItem;
import com.hbm.main.NuclearTechMod;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.player.Inventory;

import java.util.ArrayList;
import java.util.List;

public class MachineRTGScreen extends InfoScreen<MachineRTGMenu> {

    private static final ResourceLocation TEXTURE = NuclearTechMod.withDefaultNamespace("textures/gui/gui_rtg.png");

    private final MachineRTGBlockEntity be;

    public MachineRTGScreen(MachineRTGMenu menu, Inventory inventory, Component title) {
        super(menu, inventory, title);
        this.be = menu.be;
        this.imageWidth = 176;
        this.imageHeight = 188;
    }

    @Override
    public void render(GuiGraphics guiGraphics, int mouseX, int mouseY, float partialTicks) {
        super.render(guiGraphics, mouseX, mouseY, partialTicks);

        this.drawElectricityInfo(guiGraphics, mouseX, mouseY, this.leftPos + 146, this.topPos + 9, 16, 51, this.be.power, MachineRTGBlockEntity.MAX_POWER);
        this.drawCustomInfoStat(guiGraphics, mouseX, mouseY, this.leftPos + 124, this.topPos + 9, 16, 51,
                Component.translatable("desc.gui.rtg.heat", this.be.heat));

        List<Component> pellets = new ArrayList<>();
        pellets.add(Component.translatable("desc.gui.rtg.pellets"));
        for(RTGPelletItem pellet : RTGPelletItem.PELLETS) {
            pellets.add(Component.translatable("desc.gui.rtg.pelletPower", pellet.getDescription(), pellet.getHeat() * 5));
        }
        this.drawCustomInfoStat(guiGraphics, mouseX, mouseY, this.leftPos - 12, this.topPos + 25, 16, 16, this.leftPos - 8, this.topPos + 36 + 16, pellets);

        this.renderTooltip(guiGraphics, mouseX, mouseY);
    }

    @Override
    protected void renderLabels(GuiGraphics guiGraphics, int mouseX, int mouseY) {
        guiGraphics.drawString(this.font, this.title, 60 - this.font.width(this.title) / 2, 7, 10925486, false);
        guiGraphics.drawString(this.font, this.playerInventoryTitle, 8, this.imageHeight - 96 + 2, 4210752, false);
    }

    @Override
    protected void renderBg(GuiGraphics guiGraphics, float partialTicks, int mouseX, int mouseY) {
        guiGraphics.blit(TEXTURE, this.leftPos, this.topPos, 0, 0, this.imageWidth, this.imageHeight, 256, 256);

        // The client block entity's slots are the menu's container, so hasHeat() sees the synced slots while the screen is open.
        if(this.be.hasHeat()) {
            // Truncating like the original; clamped because the server's heat cap (600/200) can differ from the client's doRTGsDecay.
            int i = Math.min(51, this.be.getHeatScaled(51));
            guiGraphics.blit(TEXTURE, this.leftPos + 124, this.topPos + 61 - i, 176, 10 + (51 - i), 16, i, 256, 256);
        }

        if(this.be.hasPower()) {
            int i = (int) this.be.getPowerScaled(51);
            guiGraphics.blit(TEXTURE, this.leftPos + 146, this.topPos + 61 - i, 192, 10 + (51 - i), 16, i, 256, 256);
        }

        this.drawInfoPanel(guiGraphics, this.leftPos - 12, this.topPos + 25, 2);
    }
}
