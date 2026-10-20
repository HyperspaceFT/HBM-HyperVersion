package com.hbm.inventory.screens;

import com.hbm.blockentity.machine.rbmk.RBMKControlManualBlockEntity;
import com.hbm.inventory.menus.RBMKControlMenu;
import com.hbm.main.NuclearTechMod;
import com.hbm.network.toserver.CompoundTagControl;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.player.Inventory;
import net.neoforged.neoforge.network.PacketDistributor;
import org.lwjgl.glfw.GLFW;

/**
 * Original GUIRBMKControl: the insertion bar, five insertion buttons and five colour group buttons. The power widget (:38-40,
 * :94-96) belongs to the ReaSim control rods and is not ported.
 */
public class RBMKControlScreen extends InfoScreen<RBMKControlMenu> {

    private static final ResourceLocation TEXTURE = NuclearTechMod.withDefaultNamespace("textures/gui/reactors/gui_rbmk_control.png");

    private final RBMKControlManualBlockEntity be;

    public RBMKControlScreen(RBMKControlMenu menu, Inventory playerInventory, Component title) {
        super(menu, playerInventory, title);

        this.be = menu.be;

        this.imageWidth = 176;
        this.imageHeight = 186;
    }

    @Override
    public void render(GuiGraphics guiGraphics, int mouseX, int mouseY, float partialTicks) {
        super.render(guiGraphics, mouseX, mouseY, partialTicks);

        this.drawCustomInfoStat(guiGraphics, mouseX, mouseY, this.leftPos + 71, this.topPos + 29, 16, 56, mouseX, mouseY, Component.literal((int)(be.level * 100) + "%"));

        this.renderTooltip(guiGraphics, mouseX, mouseY);
    }

    /** Original mouseClicked (:43-67). The buttons are checked first: the container screen consumes every click inside the GUI. */
    @Override
    public boolean mouseClicked(double x, double y, int button) {
        if(button != GLFW.GLFW_MOUSE_BUTTON_LEFT) return super.mouseClicked(x, y, button);

        for(int k = 0; k < 5; k++) {

            //manual rod control
            if(leftPos + 118 <= x && leftPos + 118 + 30 > x && topPos + 26 + k * 11 < y && topPos + 26 + 10 + k * 11 >= y) {

                this.click();
                CompoundTag data = new CompoundTag();
                data.putDouble("level", 1.0D - (k * 0.25D));
                PacketDistributor.sendToServer(new CompoundTagControl(data, be.getBlockPos()));
                return true;
            }

            //color groups
            if(leftPos + 28 <= x && leftPos + 28 + 12 > x && topPos + 26 + k * 11 < y && topPos + 26 + 10 + k * 11 >= y) {

                this.click();
                CompoundTag data = new CompoundTag();
                data.putInt("color", k);
                PacketDistributor.sendToServer(new CompoundTagControl(data, be.getBlockPos()));
                return true;
            }
        }

        return super.mouseClicked(x, y, button);
    }

    @Override
    protected void renderLabels(GuiGraphics guiGraphics, int mouseX, int mouseY) {
        guiGraphics.drawString(this.font, this.title, this.imageWidth / 2 - this.font.width(this.title) / 2, 6, 4210752, false);
        guiGraphics.drawString(this.font, this.playerInventoryTitle, 8, this.imageHeight - 96 + 2, 4210752, false);
    }

    @Override
    protected void renderBg(GuiGraphics guiGraphics, float partialTicks, int mouseX, int mouseY) {
        guiGraphics.blit(TEXTURE, this.leftPos, this.topPos, 0, 0, this.imageWidth, this.imageHeight);

        int height = (int)(56 * (1D - be.level));

        if(height > 0)
            guiGraphics.blit(TEXTURE, this.leftPos + 75, this.topPos + 29, 176, 56 - height, 8, height);

        if(be.color != null) {
            int color = be.color.ordinal();

            guiGraphics.blit(TEXTURE, this.leftPos + 28, this.topPos + 26 + color * 11, 184, color * 10, 12, 10);
        }
    }
}
