package com.hbm.inventory.screens;

import com.hbm.blockentity.machine.rbmk.RBMKAutoloaderBlockEntity;
import com.hbm.inventory.menus.RBMKAutoloaderMenu;
import com.hbm.main.NuclearTechMod;
import com.hbm.network.toserver.CompoundTagControl;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.player.Inventory;
import net.neoforged.neoforge.network.PacketDistributor;
import org.lwjgl.glfw.GLFW;

/** Original GUIRBMKAutoloader: the two slot grids and the cycle threshold with its minus and plus buttons. */
public class RBMKAutoloaderScreen extends InfoScreen<RBMKAutoloaderMenu> {

    private static final ResourceLocation TEXTURE = NuclearTechMod.withDefaultNamespace("textures/gui/machine/gui_autoloader.png");

    private final RBMKAutoloaderBlockEntity be;

    public RBMKAutoloaderScreen(RBMKAutoloaderMenu menu, Inventory playerInventory, Component title) {
        super(menu, playerInventory, title);

        this.be = menu.be;

        this.imageWidth = 176;
        this.imageHeight = 182;
    }

    @Override
    public void render(GuiGraphics guiGraphics, int mouseX, int mouseY, float partialTicks) {
        super.render(guiGraphics, mouseX, mouseY, partialTicks);
        this.renderTooltip(guiGraphics, mouseX, mouseY);
    }

    /**
     * Original mouseClicked (:36-53), with its bounds (inclusive left, exclusive right, exclusive top, inclusive bottom). The buttons are
     * checked first: the container screen consumes every click inside the GUI.
     */
    @Override
    public boolean mouseClicked(double x, double y, int button) {
        // NEO-only: the buttons answer the left button only (as RBMKControlScreen); the original reacted to any button.
        if(button != GLFW.GLFW_MOUSE_BUTTON_LEFT) return super.mouseClicked(x, y, button);

        if(leftPos + 74 <= x && leftPos + 74 + 12 > x && topPos + 36 < y && topPos + 36 + 12 >= y) {
            this.click();
            CompoundTag data = new CompoundTag();
            data.putBoolean("minus", true);
            PacketDistributor.sendToServer(new CompoundTagControl(data, be.getBlockPos()));
            return true;
        }

        if(leftPos + 90 <= x && leftPos + 90 + 12 > x && topPos + 36 < y && topPos + 36 + 12 >= y) {
            this.click();
            CompoundTag data = new CompoundTag();
            data.putBoolean("plus", true);
            PacketDistributor.sendToServer(new CompoundTagControl(data, be.getBlockPos()));
            return true;
        }

        return super.mouseClicked(x, y, button);
    }

    @Override
    protected void renderLabels(GuiGraphics guiGraphics, int mouseX, int mouseY) {
        guiGraphics.drawString(this.font, this.title, this.imageWidth / 2 - this.font.width(this.title) / 2, 6, 0xFFFFFF, false);
        guiGraphics.drawString(this.font, this.playerInventoryTitle, 8, this.imageHeight - 96 + 2, 4210752, false);

        String percent = be.cycle + "%";
        guiGraphics.drawString(this.font, percent, this.imageWidth / 2 - this.font.width(percent) / 2, 23, 0x00FF00, false);
    }

    @Override
    protected void renderBg(GuiGraphics guiGraphics, float partialTicks, int mouseX, int mouseY) {
        guiGraphics.blit(TEXTURE, this.leftPos, this.topPos, 0, 0, this.imageWidth, this.imageHeight);
    }
}
