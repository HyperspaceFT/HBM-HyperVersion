package com.hbm.inventory.screens;

import com.hbm.blockentity.network.CraneRouterBlockEntity;
import com.hbm.inventory.menus.CraneRouterMenu;
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

/** Original GUICraneRouter: the 30 filter slots and one mode button per side. */
public class CraneRouterScreen extends InfoScreen<CraneRouterMenu> {

    private static final ResourceLocation TEXTURE = NuclearTechMod.withDefaultNamespace("textures/gui/storage/gui_crane_router.png");

    private final CraneRouterBlockEntity be;

    public CraneRouterScreen(CraneRouterMenu menu, Inventory playerInventory, Component title) {
        super(menu, playerInventory, title);

        this.be = menu.be;

        this.imageWidth = 256;
        this.imageHeight = 201;
        this.inventoryLabelX = 47;
        this.inventoryLabelY = this.imageHeight - 96 + 2;
    }

    private boolean isOverButton(int j, int k, double x, double y) {
        return leftPos + 7 + j * 222 <= x && leftPos + 7 + j * 222 + 18 > x && topPos + 16 + k * 26 < y && topPos + 16 + k * 26 + 18 >= y;
    }

    /** Original mouseClicked (:38-55): the button of side j * 3 + k; NEO answers the left button only, as the other NEO screens. */
    @Override
    public boolean mouseClicked(double x, double y, int button) {
        if(button == GLFW.GLFW_MOUSE_BUTTON_LEFT) {
            for(int j = 0; j < 2; j++) {
                for(int k = 0; k < 3; k++) {
                    if(this.isOverButton(j, k, x, y)) {
                        this.click();
                        CompoundTag data = new CompoundTag();
                        data.putInt("toggle", j * 3 + k);
                        PacketDistributor.sendToServer(new CompoundTagControl(data, be.getBlockPos()));
                        return true;
                    }
                }
            }
        }

        return super.mouseClicked(x, y, button);
    }

    /** Original drawScreen (:57-91), its hardcoded English now language keys. */
    @Override
    public void render(GuiGraphics guiGraphics, int mouseX, int mouseY, float partialTicks) {
        super.render(guiGraphics, mouseX, mouseY, partialTicks);

        for(int j = 0; j < 2; j++) {
            for(int k = 0; k < 3; k++) {
                if(this.isOverButton(j, k, mouseX, mouseY)) {
                    int mode = Math.clamp(be.modes[j * 3 + k], 0, 3);
                    String key = "gui.hbmsntm.crane_router.mode" + mode;
                    List<Component> text = mode == 0 ? List.of(Component.translatable(key)) : List.of(Component.translatable(key), Component.translatable(key + ".desc"));
                    guiGraphics.renderComponentTooltip(this.font, text, mouseX, mouseY);
                }
            }
        }

        if(this.menu.getCarried().isEmpty()) {
            for(int i = 0; i < 30; ++i) {
                Slot slot = this.menu.getSlot(i);
                String mode = be.patterns[i / 5].modes[i % 5];

                if(this.isHovering(slot.x, slot.y, 16, 16, mouseX, mouseY) && mode != null) {
                    guiGraphics.renderComponentTooltip(this.font, List.of(Component.translatable("gui.hbmsntm.filter.right_click").withStyle(ChatFormatting.RED), ModulePatternMatcher.getLabel(mode)), mouseX, mouseY - 30);
                }
            }
        }

        this.renderTooltip(guiGraphics, mouseX, mouseY);
    }

    @Override
    protected void renderLabels(GuiGraphics guiGraphics, int mouseX, int mouseY) {
        guiGraphics.drawString(this.font, this.title, this.imageWidth / 2 - this.font.width(this.title) / 2, 5, 4210752, false);
        guiGraphics.drawString(this.font, this.playerInventoryTitle, this.inventoryLabelX, this.inventoryLabelY, 4210752, false);
    }

    /** Original :101-114; the texture file is 256 by 256 and holds the mode buttons at u 238, v 93 + 18 * mode. */
    @Override
    protected void renderBg(GuiGraphics guiGraphics, float partialTicks, int mouseX, int mouseY) {
        guiGraphics.blit(TEXTURE, this.leftPos, this.topPos, 0, 0, 256, 93);
        guiGraphics.blit(TEXTURE, this.leftPos + 39, this.topPos + 93, 39, 93, 176, 108);

        for(int j = 0; j < 2; j++) {
            for(int k = 0; k < 3; k++) {
                int mode = Math.clamp(be.modes[j * 3 + k], 0, 3);
                guiGraphics.blit(TEXTURE, this.leftPos + 7 + j * 222, this.topPos + 16 + k * 26, 238, 93 + mode * 18, 18, 18);
            }
        }
    }
}
