package com.hbm.inventory.screens;

import com.hbm.blockentity.machine.rbmk.RBMKBoilerBlockEntity;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.menus.RBMKBoilerMenu;
import com.hbm.main.NuclearTechMod;
import com.hbm.network.toserver.CompoundTagControl;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.player.Inventory;
import net.neoforged.neoforge.network.PacketDistributor;

/** Original GUIRBMKBoiler: the feedwater and steam gauges and the compressor switch with the selected steam grade. */
public class RBMKBoilerScreen extends InfoScreen<RBMKBoilerMenu> {

    private static final ResourceLocation TEXTURE = NuclearTechMod.withDefaultNamespace("textures/gui/reactors/gui_rbmk_boiler.png");

    private final RBMKBoilerBlockEntity be;

    public RBMKBoilerScreen(RBMKBoilerMenu menu, Inventory playerInventory, Component title) {
        super(menu, playerInventory, title);

        this.be = menu.be;

        this.imageWidth = 176;
        this.imageHeight = 186;
    }

    @Override
    public void render(GuiGraphics guiGraphics, int mouseX, int mouseY, float partialTicks) {
        super.render(guiGraphics, mouseX, mouseY, partialTicks);

        be.feed.renderTankTooltip(guiGraphics, mouseX, mouseY, this.leftPos + 126, this.topPos + 24, 16, 56);
        be.steam.renderTankTooltip(guiGraphics, mouseX, mouseY, this.leftPos + 89, this.topPos + 39, 8, 28);

        this.renderTooltip(guiGraphics, mouseX, mouseY);
    }

    /** Original mouseClicked (:41-52). The switch is checked first: the container screen consumes every click inside the GUI. */
    @Override
    public boolean mouseClicked(double x, double y, int button) {

        if(leftPos + 33 <= x && leftPos + 33 + 20 > x && topPos + 21 < y && topPos + 21 + 64 >= y) {

            this.click();
            CompoundTag data = new CompoundTag();
            data.putBoolean("compression", true); //we only need to send on bit, so boolean it is
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

        int i = be.feed.getFill() * 58 / be.feed.getMaxFill();
        guiGraphics.blit(TEXTURE, this.leftPos + 126, this.topPos + 82 - i, 176, 58 - i, 14, i);

        int j = be.steam.getFill() * 22 / be.steam.getMaxFill();

        if(j > 0) j++;
        if(j > 22) j++;

        guiGraphics.blit(TEXTURE, this.leftPos + 91, this.topPos + 65 - j, 190, 24 - j, 4, j);

        FluidType type = be.steam.getTankType();
        if(type == Fluids.STEAM) guiGraphics.blit(TEXTURE, this.leftPos + 36, this.topPos + 24, 194, 0, 14, 58);
        if(type == Fluids.HOTSTEAM) guiGraphics.blit(TEXTURE, this.leftPos + 36, this.topPos + 24, 208, 0, 14, 58);
        if(type == Fluids.SUPERHOTSTEAM) guiGraphics.blit(TEXTURE, this.leftPos + 36, this.topPos + 24, 222, 0, 14, 58);
        if(type == Fluids.ULTRAHOTSTEAM) guiGraphics.blit(TEXTURE, this.leftPos + 36, this.topPos + 24, 236, 0, 14, 58);
    }
}
