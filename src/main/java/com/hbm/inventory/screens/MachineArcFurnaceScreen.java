package com.hbm.inventory.screens;

import com.hbm.blockentity.machine.MachineArcFurnaceBlockEntity;
import com.hbm.inventory.menus.MachineArcFurnaceMenu;
import com.hbm.main.NuclearTechMod;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.player.Inventory;

/** Original GUIMachineArcFurnaceLarge, solid mode only (Goal 13B B1). */
public class MachineArcFurnaceScreen extends InfoScreen<MachineArcFurnaceMenu> {

    private static final ResourceLocation TEXTURE = NuclearTechMod.withDefaultNamespace("textures/gui/processing/gui_arc_furnace.png");

    /** Progress bar rectangle, the JEI click area follows it. */
    public static final int PROGRESS_X = 17;
    public static final int PROGRESS_Y = 36;
    public static final int PROGRESS_WIDTH = 7;
    public static final int PROGRESS_HEIGHT = 70;

    private final MachineArcFurnaceBlockEntity be;

    public MachineArcFurnaceScreen(MachineArcFurnaceMenu menu, Inventory inventory, Component title) {
        super(menu, inventory, title);
        this.be = menu.be;
        this.imageWidth = 176;
        this.imageHeight = 256;
    }

    @Override
    public void render(GuiGraphics guiGraphics, int mouseX, int mouseY, float partialTicks) {
        super.render(guiGraphics, mouseX, mouseY, partialTicks);
        // The original liquid bar tooltip (152, 36, 16 x 70) and the liquid mode button (151, 17, 18 x 18) are not
        // ported, there is no liquid mode (B1); that part of the texture stays unused.
        this.drawElectricityInfo(guiGraphics, mouseX, mouseY, this.leftPos + 8, this.topPos + 36, 7, 70, this.be.getPower(), this.be.getMaxPower());
        this.renderTooltip(guiGraphics, mouseX, mouseY);
    }

    @Override
    protected void renderLabels(GuiGraphics guiGraphics, int mouseX, int mouseY) {
        // the original draws the title in white, on the dark grid panel of the texture
        guiGraphics.drawString(this.font, this.title, this.imageWidth / 2 - this.font.width(this.title) / 2, 6, 0xffffff, false);
        guiGraphics.drawString(this.font, this.playerInventoryTitle, 8, this.imageHeight - 96 + 2, 4210752, false);
    }

    @Override
    protected void renderBg(GuiGraphics guiGraphics, float partialTicks, int mouseX, int mouseY) {
        guiGraphics.blit(TEXTURE, this.leftPos, this.topPos, 0, 0, this.imageWidth, this.imageHeight);

        if(this.be.isProgressing) guiGraphics.blit(TEXTURE, this.leftPos + 7, this.topPos + 17, 190, 0, 18, 18);

        int p = (int) (this.be.power * 70 / Math.max(this.be.getMaxPower(), 1));
        guiGraphics.blit(TEXTURE, this.leftPos + 8, this.topPos + 106 - p, 176, 70 - p, 7, p);

        int o = (int) (this.be.progress * 70);
        guiGraphics.blit(TEXTURE, this.leftPos + PROGRESS_X, this.topPos + 106 - o, 183, 70 - o, PROGRESS_WIDTH, o);
    }
}
