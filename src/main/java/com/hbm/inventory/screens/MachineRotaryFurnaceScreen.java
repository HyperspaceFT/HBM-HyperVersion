package com.hbm.inventory.screens;

import com.hbm.blockentity.machine.MachineRotaryFurnaceBlockEntity;
import com.hbm.inventory.menus.MachineRotaryFurnaceMenu;
import com.hbm.main.NuclearTechMod;
import com.mojang.blaze3d.systems.RenderSystem;
import net.minecraft.ChatFormatting;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.inventory.Slot;

import java.util.Optional;

public class MachineRotaryFurnaceScreen extends InfoScreen<MachineRotaryFurnaceMenu> {

    private static final ResourceLocation TEXTURE = NuclearTechMod.withDefaultNamespace("textures/gui/processing/gui_rotary_furnace.png");

    private final MachineRotaryFurnaceBlockEntity be;

    public MachineRotaryFurnaceScreen(MachineRotaryFurnaceMenu menu, Inventory inventory, Component title) {
        super(menu, inventory, title);
        this.be = menu.be;
        this.imageWidth = 176;
        this.imageHeight = 186;
    }

    @Override
    public void render(GuiGraphics guiGraphics, int mouseX, int mouseY, float partialTicks) {
        super.render(guiGraphics, mouseX, mouseY, partialTicks);

        this.be.tanks[0].renderTankTooltip(guiGraphics, mouseX, mouseY, this.leftPos + 8, this.topPos + 36, 52, 16);
        this.be.tanks[1].renderTankTooltip(guiGraphics, mouseX, mouseY, this.leftPos + 134, this.topPos + 18, 16, 52);
        this.be.tanks[2].renderTankTooltip(guiGraphics, mouseX, mouseY, this.leftPos + 152, this.topPos + 18, 16, 52);

        Slot slot = this.menu.slots.get(4);
        if(!slot.hasItem() && this.isHovering(slot.x, slot.y, 16, 16, mouseX, mouseY)) {
            guiGraphics.renderTooltip(this.font, MachineRotaryFurnaceBlockEntity.BURN_MODULE.getDesc(), Optional.empty(), mouseX, mouseY);
        }

        if(this.be.output == null) {
            this.drawCustomInfoStat(guiGraphics, mouseX, mouseY, this.leftPos + 98, this.topPos + 18, 16, 52, mouseX, mouseY,
                    Component.translatable("container.machineRotaryFurnace.empty").withStyle(ChatFormatting.RED));
        } else {
            this.drawCustomInfoStat(guiGraphics, mouseX, mouseY, this.leftPos + 98, this.topPos + 18, 16, 52, mouseX, mouseY,
                    Component.empty().append(this.be.output.material.getName()).append(": " + this.be.output.amount).withStyle(ChatFormatting.YELLOW));
        }

        this.renderTooltip(guiGraphics, mouseX, mouseY);
    }

    @Override
    protected void renderLabels(GuiGraphics guiGraphics, int mouseX, int mouseY) {
        guiGraphics.drawString(this.font, this.title, (this.imageWidth - 54) / 2 - this.font.width(this.title) / 2, 6, 4210752, false);
        guiGraphics.drawString(this.font, this.playerInventoryTitle, 8, this.imageHeight - 96 + 2, 4210752, false);
    }

    @Override
    protected void renderBg(GuiGraphics guiGraphics, float partialTicks, int mouseX, int mouseY) {
        guiGraphics.blit(TEXTURE, this.leftPos, this.topPos, 0, 0, this.imageWidth, this.imageHeight);

        int p = (int) Math.ceil(this.be.progress * 33);
        guiGraphics.blit(TEXTURE, this.leftPos + 63, this.topPos + 30, 176, 0, p, 10);

        if(this.be.maxBurnTime > 0) {
            int b = this.be.burnTime * 14 / this.be.maxBurnTime;
            guiGraphics.blit(TEXTURE, this.leftPos + 26, this.topPos + 69 - b, 176, 24 - b, 14, b);
        }

        if(this.be.output != null) {
            int hex = this.be.output.material.moltenColor;
            int amount = this.be.output.amount * 52 / MachineRotaryFurnaceBlockEntity.MAX_OUTPUT;

            guiGraphics.setColor((hex >> 16 & 255) / 255F, (hex >> 8 & 255) / 255F, (hex & 255) / 255F, 1F);
            guiGraphics.blit(TEXTURE, this.leftPos + 98, this.topPos + 70 - amount, 176, 76 - amount, 16, amount);
            RenderSystem.enableBlend();
            guiGraphics.setColor(1F, 1F, 1F, 0.3F);
            guiGraphics.blit(TEXTURE, this.leftPos + 98, this.topPos + 70 - amount, 176, 76 - amount, 16, amount);
            RenderSystem.disableBlend();
            guiGraphics.setColor(1F, 1F, 1F, 1F);
        }

        this.be.tanks[0].renderTank(this.leftPos + 8, this.topPos + 52, 0, 52, 16, 1);
        this.be.tanks[1].renderTank(this.leftPos + 134, this.topPos + 70, 0, 16, 52);
        this.be.tanks[2].renderTank(this.leftPos + 152, this.topPos + 70, 0, 16, 52);
    }
}
