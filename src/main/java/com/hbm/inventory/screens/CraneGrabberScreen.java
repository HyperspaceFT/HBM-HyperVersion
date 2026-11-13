package com.hbm.inventory.screens;

import com.hbm.blockentity.network.CraneGrabberBlockEntity;
import com.hbm.inventory.menus.CraneGrabberMenu;
import com.hbm.main.NuclearTechMod;
import com.hbm.module.ModulePatternMatcher;
import com.hbm.network.toserver.CompoundTagControl;
import net.minecraft.ChatFormatting;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.inventory.Slot;
import net.neoforged.neoforge.network.PacketDistributor;
import org.lwjgl.glfw.GLFW;

import java.util.List;

/** Original GUICraneGrabber: filter, upgrades and the whitelist switch. */
public class CraneGrabberScreen extends InfoScreen<CraneGrabberMenu> {

    private static final ResourceLocation TEXTURE = NuclearTechMod.withDefaultNamespace("textures/gui/storage/gui_crane_grabber.png");

    private final CraneGrabberBlockEntity be;

    public CraneGrabberScreen(CraneGrabberMenu menu, Inventory playerInventory, Component title) {
        super(menu, playerInventory, title);

        this.be = menu.be;

        this.imageWidth = 176;
        this.imageHeight = 185;
    }

    /** Original drawScreen (:36-49), its hardcoded English now the extractor screen's language key. */
    @Override
    public void render(GuiGraphics guiGraphics, int mouseX, int mouseY, float partialTicks) {
        super.render(guiGraphics, mouseX, mouseY, partialTicks);

        if(this.menu.getCarried().isEmpty()) {
            for(int i = 0; i < 9; ++i) {
                Slot slot = this.menu.getSlot(i);

                if(this.isHovering(slot.x, slot.y, 16, 16, mouseX, mouseY) && be.matcher.modes[i] != null) {
                    guiGraphics.renderComponentTooltip(this.font, List.of(Component.translatable("gui.hbmsntm.filter.right_click").withStyle(ChatFormatting.RED), ModulePatternMatcher.getLabel(be.matcher.modes[i])), mouseX, mouseY - 30);
                }
            }
        }

        this.renderTooltip(guiGraphics, mouseX, mouseY);
    }

    /** Original mouseClicked (:52-62), with its bounds; NEO answers the left button only, as the other NEO screens. */
    @Override
    public boolean mouseClicked(double x, double y, int button) {
        if(button == GLFW.GLFW_MOUSE_BUTTON_LEFT && leftPos + 97 <= x && leftPos + 97 + 14 > x && topPos + 30 < y && topPos + 30 + 26 >= y) {
            this.click();
            CompoundTag data = new CompoundTag();
            data.putBoolean("whitelist", true);
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

    @Override
    protected void renderBg(GuiGraphics guiGraphics, float partialTicks, int mouseX, int mouseY) {
        guiGraphics.blit(TEXTURE, this.leftPos, this.topPos, 0, 0, this.imageWidth, this.imageHeight);

        if(be.isWhitelist) {
            guiGraphics.blit(TEXTURE, this.leftPos + 108, this.topPos + 33, 176, 0, 3, 6);
        } else {
            guiGraphics.blit(TEXTURE, this.leftPos + 108, this.topPos + 47, 176, 0, 3, 6);
        }
    }
}
