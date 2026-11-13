package com.hbm.inventory.screens;

import com.hbm.blockentity.network.CraneExtractorBlockEntity;
import com.hbm.inventory.menus.CraneExtractorMenu;
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

/** Original GUICraneExtractor: filter, buffer, upgrades, the whitelist switch and the maxEject switch. */
public class CraneExtractorScreen extends InfoScreen<CraneExtractorMenu> {

    private static final ResourceLocation TEXTURE = NuclearTechMod.withDefaultNamespace("textures/gui/storage/gui_crane_ejector.png");

    private final CraneExtractorBlockEntity be;

    public CraneExtractorScreen(CraneExtractorMenu menu, Inventory playerInventory, Component title) {
        super(menu, playerInventory, title);

        this.be = menu.be;

        this.imageWidth = 212;
        this.imageHeight = 185;
    }

    /** Original drawScreen (:33-52), its hardcoded English now language keys. */
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

        if(leftPos + 187 <= mouseX && leftPos + 187 + 18 > mouseX && topPos + 34 < mouseY && topPos + 34 + 18 >= mouseY) {
            Component state = be.maxEject ? Component.translatable("gui.hbmsntm.crane.on").withStyle(ChatFormatting.GREEN) : Component.translatable("gui.hbmsntm.crane.off").withStyle(ChatFormatting.RED);
            guiGraphics.renderTooltip(this.font, Component.translatable("gui.hbmsntm.crane_extractor.max_eject", state), mouseX, mouseY);
        }

        this.renderTooltip(guiGraphics, mouseX, mouseY);
    }

    /** Original mouseClicked (:55-73), with its bounds; NEO answers the left button only, as the other NEO screens. */
    @Override
    public boolean mouseClicked(double x, double y, int button) {
        if(button == GLFW.GLFW_MOUSE_BUTTON_LEFT) {

            if(leftPos + 187 <= x && leftPos + 187 + 18 > x && topPos + 34 < y && topPos + 34 + 18 >= y) {
                this.send("maxEject");
                return true;
            }

            if(leftPos + 128 <= x && leftPos + 128 + 14 > x && topPos + 30 < y && topPos + 30 + 26 >= y) {
                this.send("whitelist");
                return true;
            }
        }

        return super.mouseClicked(x, y, button);
    }

    private void send(String key) {
        this.click();
        CompoundTag data = new CompoundTag();
        data.putBoolean(key, true);
        PacketDistributor.sendToServer(new CompoundTagControl(data, be.getBlockPos()));
    }

    @Override
    protected void renderLabels(GuiGraphics guiGraphics, int mouseX, int mouseY) {
        guiGraphics.drawString(this.font, this.title, this.imageWidth / 2 - this.font.width(this.title) / 2, 6, 4210752, false);
        guiGraphics.drawString(this.font, this.playerInventoryTitle, 26, this.imageHeight - 96 + 2, 4210752, false);
    }

    @Override
    protected void renderBg(GuiGraphics guiGraphics, float partialTicks, int mouseX, int mouseY) {
        guiGraphics.blit(TEXTURE, this.leftPos, this.topPos, 0, 0, this.imageWidth, this.imageHeight);

        if(be.maxEject) guiGraphics.blit(TEXTURE, this.leftPos + 187, this.topPos + 34, 212, 0, 18, 18);

        if(be.isWhitelist) {
            guiGraphics.blit(TEXTURE, this.leftPos + 139, this.topPos + 33, 212, 18, 3, 6);
        } else {
            guiGraphics.blit(TEXTURE, this.leftPos + 139, this.topPos + 47, 212, 18, 3, 6);
        }
    }
}
