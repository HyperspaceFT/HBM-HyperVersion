package com.hbm.inventory.screens;

import com.hbm.blockentity.machine.MachineElectricFurnaceBlockEntity;
import com.hbm.blocks.machine.MachineElectricFurnaceBlock;
import com.hbm.inventory.menus.MachineElectricFurnaceMenu;
import com.hbm.main.NuclearTechMod;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.level.block.state.BlockState;

import java.util.List;

public class MachineElectricFurnaceScreen extends InfoScreen<MachineElectricFurnaceMenu> {

    private static final ResourceLocation TEXTURE = NuclearTechMod.withDefaultNamespace("textures/gui/processing/gui_electric_furnace.png");

    private final MachineElectricFurnaceBlockEntity be;

    public MachineElectricFurnaceScreen(MachineElectricFurnaceMenu menu, Inventory inventory, Component title) {
        super(menu, inventory, title);
        this.be = menu.be;
        this.imageWidth = 176;
        this.imageHeight = 186;
    }

    @Override
    public void render(GuiGraphics guiGraphics, int mouseX, int mouseY, float partialTicks) {
        super.render(guiGraphics, mouseX, mouseY, partialTicks);

        this.drawElectricityInfo(guiGraphics, mouseX, mouseY, this.leftPos + 152, this.topPos + 52 - 34, 16, 34, this.be.getPower(), this.be.getMaxPower());

        List<Component> upgradeInfo = List.of(
                Component.translatable("container.upgrade"),
                Component.translatable("container.upgrade.speed"),
                Component.translatable("container.upgrade.power")
        );
        this.drawCustomInfoStat(guiGraphics, mouseX, mouseY, this.leftPos + 115, this.topPos + 19, 8, 8, mouseX, mouseY, upgradeInfo);

        this.renderTooltip(guiGraphics, mouseX, mouseY);
    }

    @Override
    protected void renderLabels(GuiGraphics guiGraphics, int mouseX, int mouseY) {
        guiGraphics.drawString(this.font, this.title, 70 - this.font.width(this.title) / 2, 6, 4210752, false);
        guiGraphics.drawString(this.font, this.playerInventoryTitle, 8, this.imageHeight - 96 + 2, 4210752, false);
    }

    @Override
    protected void renderBg(GuiGraphics guiGraphics, float partialTicks, int mouseX, int mouseY) {
        guiGraphics.blit(TEXTURE, this.leftPos, this.topPos, 0, 0, this.imageWidth, this.imageHeight);

        if(this.be.hasPower()) {
            int p = (int) this.be.getPowerScaled(34);
            guiGraphics.blit(TEXTURE, this.leftPos + 152, this.topPos + 52 - p, 176, 64 - p, 16, p);
        }

        BlockState state = this.be.getBlockState();
        if(state.hasProperty(MachineElectricFurnaceBlock.LIT) && state.getValue(MachineElectricFurnaceBlock.LIT)) {
            guiGraphics.blit(TEXTURE, this.leftPos + 45, this.topPos + 20, 192, 12, 18, 16);
            guiGraphics.blit(TEXTURE, this.leftPos + 46, this.topPos + 47, 192, 28, 18, 16);
        }

        int p = this.be.getProgressScaled(28);
        guiGraphics.blit(TEXTURE, this.leftPos + 43, this.topPos + 36, 176, 0, p, 12);

        this.drawInfoPanel(guiGraphics, this.leftPos + 115, this.topPos + 19, 8);
    }
}
