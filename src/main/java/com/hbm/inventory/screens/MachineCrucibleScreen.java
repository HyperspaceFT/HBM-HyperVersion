package com.hbm.inventory.screens;

import com.hbm.blockentity.machine.MachineCrucibleBlockEntity;
import com.hbm.inventory.menus.MachineCrucibleMenu;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.network.chat.Component;
import net.minecraft.world.entity.player.Inventory;

public class MachineCrucibleScreen extends InfoScreen<MachineCrucibleMenu> {

    private final MachineCrucibleBlockEntity be;

    public MachineCrucibleScreen(MachineCrucibleMenu menu, Inventory inventory, Component title) {
        super(menu, inventory, title);
        this.be = menu.be;
        this.imageWidth = 176;
        this.imageHeight = 186;
    }

    @Override
    public void render(GuiGraphics graphics, int mouseX, int mouseY, float partialTicks) {
        super.render(graphics, mouseX, mouseY, partialTicks);
        this.drawCustomInfoStat(graphics, mouseX, mouseY, leftPos + 110, topPos + 21, 52, 9, mouseX, mouseY,
                Component.translatable("container.machine_crucible.heat", be.heat, MachineCrucibleBlockEntity.MAX_HEAT),
                Component.translatable("container.machine_crucible.heat_requirement"));
        this.drawCustomInfoStat(graphics, mouseX, mouseY, leftPos + 110, topPos + 42, 52, 9, mouseX, mouseY,
                Component.translatable("container.machine_crucible.progress", be.progress, MachineCrucibleBlockEntity.PROCESS_TIME),
                Component.translatable("container.machine_crucible.placement"));
        this.drawCustomInfoStat(graphics, mouseX, mouseY, leftPos + 110, topPos + 63, 52, 9, mouseX, mouseY,
                Component.translatable("container.machine_crucible.copper", be.copper, MachineCrucibleBlockEntity.CAPACITY),
                Component.translatable("container.machine_crucible.pour"));
        this.renderTooltip(graphics, mouseX, mouseY);
    }

    @Override
    protected void renderLabels(GuiGraphics graphics, int mouseX, int mouseY) {
        graphics.drawString(font, title, imageWidth / 2 - font.width(title) / 2, 6, 0x404040, false);
        graphics.drawString(font, playerInventoryTitle, 8, imageHeight - 96 + 2, 0x404040, false);
    }

    @Override
    protected void renderBg(GuiGraphics graphics, float partialTicks, int mouseX, int mouseY) {
        graphics.fill(leftPos, topPos, leftPos + imageWidth, topPos + imageHeight, 0xffc6c6c6);
        graphics.fill(leftPos + 4, topPos + 4, leftPos + imageWidth - 4, topPos + imageHeight - 4, 0xffdedede);
        for(int row = 0; row < 3; row++) {
            for(int col = 0; col < 3; col++) {
                int x = leftPos + 43 + col * 18;
                int y = topPos + 17 + row * 18;
                graphics.fill(x, y, x + 18, y + 18, 0xff777777);
                graphics.fill(x + 1, y + 1, x + 17, y + 17, 0xff373737);
            }
        }
        int[] values = {be.heat, be.progress, be.copper};
        int[] maximum = {MachineCrucibleBlockEntity.MAX_HEAT, MachineCrucibleBlockEntity.PROCESS_TIME, MachineCrucibleBlockEntity.CAPACITY};
        for(int i = 0; i < 3; i++) {
            int y = topPos + 21 + i * 21;
            graphics.fill(leftPos + 110, y, leftPos + 162, y + 9, 0xff666666);
            int width = Math.max(0, Math.min(52, values[i] * 52 / Math.max(1, maximum[i])));
            if(width > 0) graphics.fill(leftPos + 110, y, leftPos + 110 + width, y + 9,
                    i == 0 ? 0xffe87534 : i == 1 ? 0xffcfb34c : 0xffbb764e);
        }
        for(int row = 0; row < 3; row++) {
            for(int col = 0; col < 9; col++) {
                int x = leftPos + 7 + col * 18;
                int y = topPos + 103 + row * 18;
                graphics.fill(x, y, x + 18, y + 18, 0xff777777);
                graphics.fill(x + 1, y + 1, x + 17, y + 17, 0xff373737);
            }
        }
        for(int col = 0; col < 9; col++) {
            int x = leftPos + 7 + col * 18;
            int y = topPos + 161;
            graphics.fill(x, y, x + 18, y + 18, 0xff777777);
            graphics.fill(x + 1, y + 1, x + 17, y + 17, 0xff373737);
        }
    }
}
