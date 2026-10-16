package com.hbm.inventory.screens;

import com.hbm.inventory.menus.MachineWasteDrumMenu;
import com.hbm.main.NuclearTechMod;
import com.hbm.util.i18n.I18nUtil;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.player.Inventory;

import java.util.ArrayList;
import java.util.List;

/** Original GUIWasteDrum; its hard-coded English info text became the desc.gui.wasteDrum.info key. */
public class MachineWasteDrumScreen extends InfoScreen<MachineWasteDrumMenu> {

    private static final ResourceLocation TEXTURE = NuclearTechMod.withDefaultNamespace("textures/gui/gui_waste_drum.png");

    public MachineWasteDrumScreen(MachineWasteDrumMenu menu, Inventory playerInventory, Component title) {
        super(menu, playerInventory, title);

        this.imageWidth = 176;
        this.imageHeight = 189;
    }

    @Override
    protected void init() {
        super.init();

        this.titleLabelX = this.imageWidth / 2 - this.font.width(this.title) / 2;
        this.titleLabelY = 6;
        this.inventoryLabelX = 8;
        this.inventoryLabelY = this.imageHeight - 96 + 5;
    }

    @Override
    public void render(GuiGraphics guiGraphics, int mouseX, int mouseY, float partialTicks) {
        super.render(guiGraphics, mouseX, mouseY, partialTicks);

        List<Component> info = new ArrayList<>(); for(String s : I18nUtil.resolveKeyArray("desc.gui.wasteDrum.info")) info.add(Component.literal(s));
        this.drawCustomInfoStat(guiGraphics, mouseX, mouseY, this.leftPos - 16, this.topPos + 36, 16, 16, this.leftPos - 8, this.topPos + 36 + 16, info);

        this.renderTooltip(guiGraphics, mouseX, mouseY);
    }

    @Override
    protected void renderBg(GuiGraphics guiGraphics, float v, int i, int partialTicks) {
        guiGraphics.blit(TEXTURE, this.leftPos, this.topPos, 0, 0, imageWidth, imageHeight);

        this.drawInfoPanel(guiGraphics, this.leftPos - 16, this.topPos + 36, 2);
    }
}
