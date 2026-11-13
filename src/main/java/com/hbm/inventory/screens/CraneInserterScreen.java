package com.hbm.inventory.screens;

import com.hbm.blockentity.network.CraneInserterBlockEntity;
import com.hbm.inventory.menus.CraneInserterMenu;
import com.hbm.main.NuclearTechMod;
import com.hbm.network.toserver.CompoundTagControl;
import net.minecraft.ChatFormatting;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.player.Inventory;
import net.neoforged.neoforge.network.PacketDistributor;
import org.lwjgl.glfw.GLFW;

/** Original GUICraneInserter: the buffer and the destroyer switch. */
public class CraneInserterScreen extends InfoScreen<CraneInserterMenu> {

    private static final ResourceLocation TEXTURE = NuclearTechMod.withDefaultNamespace("textures/gui/storage/gui_crane_inserter.png");

    private final CraneInserterBlockEntity be;

    public CraneInserterScreen(CraneInserterMenu menu, Inventory playerInventory, Component title) {
        super(menu, playerInventory, title);

        this.be = menu.be;

        this.imageWidth = 176;
        this.imageHeight = 185;
    }

    /** Original drawScreen (:31-37), its hardcoded "Destroy overflow" text now a language key. */
    @Override
    public void render(GuiGraphics guiGraphics, int mouseX, int mouseY, float partialTicks) {
        super.render(guiGraphics, mouseX, mouseY, partialTicks);

        if(leftPos + 151 <= mouseX && leftPos + 151 + 18 > mouseX && topPos + 34 < mouseY && topPos + 34 + 18 >= mouseY) {
            Component state = be.destroyer ? Component.translatable("gui.hbmsntm.crane.on").withStyle(ChatFormatting.GREEN) : Component.translatable("gui.hbmsntm.crane.off").withStyle(ChatFormatting.RED);
            guiGraphics.renderTooltip(this.font, Component.translatable("gui.hbmsntm.crane_inserter.destroyer", state), mouseX, mouseY);
        }

        this.renderTooltip(guiGraphics, mouseX, mouseY);
    }

    /** Original mouseClicked (:39-49), with its bounds; NEO answers the left button only, as the other NEO screens. */
    @Override
    public boolean mouseClicked(double x, double y, int button) {
        if(button == GLFW.GLFW_MOUSE_BUTTON_LEFT && leftPos + 151 <= x && leftPos + 151 + 18 > x && topPos + 34 < y && topPos + 34 + 18 >= y) {
            this.click();
            CompoundTag data = new CompoundTag();
            data.putBoolean("destroyer", true);
            PacketDistributor.sendToServer(new CompoundTagControl(data, be.getBlockPos()));
            return true;
        }

        return super.mouseClicked(x, y, button);
    }

    @Override
    protected void renderLabels(GuiGraphics guiGraphics, int mouseX, int mouseY) {
        guiGraphics.drawString(this.font, this.title, this.imageWidth / 2 - this.font.width(this.title) / 2 - 18, 5, 4210752, false);
        guiGraphics.drawString(this.font, this.playerInventoryTitle, 8, this.imageHeight - 96 + 2, 4210752, false);
    }

    @Override
    protected void renderBg(GuiGraphics guiGraphics, float partialTicks, int mouseX, int mouseY) {
        guiGraphics.blit(TEXTURE, this.leftPos, this.topPos, 0, 0, this.imageWidth, this.imageHeight);

        if(be.destroyer) guiGraphics.blit(TEXTURE, this.leftPos + 151, this.topPos + 34, 176, 0, 18, 18);
    }
}
