package com.hbm.inventory.screens;

import com.hbm.blockentity.network.CraneBoxerBlockEntity;
import com.hbm.inventory.menus.CraneBoxerMenu;
import com.hbm.main.NuclearTechMod;
import com.hbm.network.toserver.CompoundTagControl;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.player.Inventory;
import net.neoforged.neoforge.network.PacketDistributor;
import org.lwjgl.glfw.GLFW;

/** Original GUICraneBoxer: the buffer and the mode button. */
public class CraneBoxerScreen extends InfoScreen<CraneBoxerMenu> {

    private static final ResourceLocation TEXTURE = NuclearTechMod.withDefaultNamespace("textures/gui/storage/gui_crane_boxer.png");

    private final CraneBoxerBlockEntity be;

    public CraneBoxerScreen(CraneBoxerMenu menu, Inventory playerInventory, Component title) {
        super(menu, playerInventory, title);

        this.be = menu.be;

        this.imageWidth = 176;
        this.imageHeight = 185;
    }

    @Override
    public void render(GuiGraphics guiGraphics, int mouseX, int mouseY, float partialTicks) {
        super.render(guiGraphics, mouseX, mouseY, partialTicks);
        this.renderTooltip(guiGraphics, mouseX, mouseY);
    }

    /** Original mouseClicked (:33-43), with its bounds; NEO answers the left button only, as the other NEO screens. */
    @Override
    public boolean mouseClicked(double x, double y, int button) {
        if(button == GLFW.GLFW_MOUSE_BUTTON_LEFT && leftPos + 151 <= x && leftPos + 151 + 18 > x && topPos + 34 < y && topPos + 34 + 18 >= y) {
            this.click();
            CompoundTag data = new CompoundTag();
            data.putBoolean("toggle", true);
            PacketDistributor.sendToServer(new CompoundTagControl(data, be.getBlockPos()));
            return true;
        }

        return super.mouseClicked(x, y, button);
    }

    @Override
    protected void renderLabels(GuiGraphics guiGraphics, int mouseX, int mouseY) {
        guiGraphics.drawString(this.font, this.title, this.imageWidth / 2 - this.font.width(this.title) / 2, 6, 4210752, false);
        guiGraphics.drawString(this.font, this.playerInventoryTitle, 8, this.imageHeight - 96 + 2, 4210752, false);
    }

    /** Original :52-58: the mode button is the 18x18 tile at (176, mode * 18). */
    @Override
    protected void renderBg(GuiGraphics guiGraphics, float partialTicks, int mouseX, int mouseY) {
        guiGraphics.blit(TEXTURE, this.leftPos, this.topPos, 0, 0, this.imageWidth, this.imageHeight);
        guiGraphics.blit(TEXTURE, this.leftPos + 151, this.topPos + 34, 176, be.mode * 18, 18, 18);
    }
}
