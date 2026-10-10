package com.hbm.inventory.screens;

import com.hbm.blockentity.machine.MachineDieselBlockEntity;
import com.hbm.inventory.menus.MachineDieselMenu;
import com.hbm.main.NuclearTechMod;
import com.hbm.network.toserver.CompoundTagControl;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.player.Inventory;
import net.neoforged.neoforge.network.PacketDistributor;

public class MachineDieselScreen extends InfoScreen<MachineDieselMenu> {

    private static final ResourceLocation TEXTURE = NuclearTechMod.withDefaultNamespace("textures/gui/generators/gui_diesel.png");

    private final MachineDieselBlockEntity be;

    public MachineDieselScreen(MachineDieselMenu menu, Inventory inventory, Component title) {
        super(menu, inventory, title);
        this.be = menu.be;
        this.imageWidth = 176;
        this.imageHeight = 203;
    }

    @Override
    public void render(GuiGraphics guiGraphics, int mouseX, int mouseY, float partialTicks) {
        super.render(guiGraphics, mouseX, mouseY, partialTicks);

        this.be.tank.renderTankTooltip(guiGraphics, mouseX, mouseY, this.leftPos + 35, this.topPos + 17, 16, 52);
        this.drawElectricityInfo(guiGraphics, mouseX, mouseY, this.leftPos + 141, this.topPos + 17, 16, 52, this.be.power, this.be.powerCap);

        this.drawInfoPanel(guiGraphics, this.leftPos - 8, this.topPos + 36, 2);
        this.drawCustomInfoStat(guiGraphics, mouseX, mouseY, this.leftPos - 8, this.topPos + 36, 16, 16, this.leftPos, this.topPos + 52,
                Component.translatable("machine_diesel.fuel_rate.title"),
                Component.translatable("machine_diesel.fuel_rate.tick"),
                Component.translatable("machine_diesel.fuel_rate.second"),
                Component.translatable("machine_diesel.fuel_rate.constant"),
                Component.translatable("machine_diesel.warning.full"));

        if(!this.be.hasAcceptableFuel()) {
            this.drawInfoPanel(guiGraphics, this.leftPos - 8, this.topPos + 68, 6);
            this.drawCustomInfoStat(guiGraphics, mouseX, mouseY, this.leftPos - 8, this.topPos + 68, 16, 16, this.leftPos, this.topPos + 84,
                    Component.translatable("machine_diesel.warning.unsupported_fuel"));
        }

        if(this.be.tank.getFill() > 0) {
            this.drawInfoPanel(guiGraphics, this.leftPos - 8, this.topPos + 84, 7);
            this.drawCustomInfoStat(guiGraphics, mouseX, mouseY, this.leftPos - 8, this.topPos + 84, 16, 16, mouseX, mouseY,
                    Component.translatable("machine_diesel.warning.type"));
        }

        this.drawCustomInfoStat(guiGraphics, mouseX, mouseY, this.leftPos + 89, this.topPos + 61, 16, 14, mouseX, mouseY,
                Component.translatable("machine_diesel.action.toggle"),
                Component.translatable(this.be.isOn ? "machine_diesel.status.on" : "machine_diesel.status.off"));
        this.drawCustomInfoStat(guiGraphics, mouseX, mouseY, this.leftPos + 89, this.topPos + 42, 16, 16, mouseX, mouseY,
                Component.translatable(this.be.wasOn ? "machine_diesel.status.running" : "machine_diesel.status.idle"));

        this.renderTooltip(guiGraphics, mouseX, mouseY);
    }

    @Override
    protected void renderLabels(GuiGraphics guiGraphics, int mouseX, int mouseY) {
        guiGraphics.drawString(this.font, this.title, this.imageWidth / 2 - this.font.width(this.title) / 2, 6, 4210752, false);
        guiGraphics.drawString(this.font, this.playerInventoryTitle, 8, this.imageHeight - 96 + 2, 4210752, false);
    }

    @Override
    protected void renderBg(GuiGraphics guiGraphics, float partialTicks, int mouseX, int mouseY) {
        guiGraphics.blit(TEXTURE, this.leftPos, this.topPos, 0, 0, this.imageWidth, this.imageHeight, 256, 256);

        int power = (int) Math.max(0L, Math.min(52L, this.be.getPowerScaled(52)));
        if(power > 0) {
            guiGraphics.blit(TEXTURE, this.leftPos + 141, this.topPos + 69 - power, 176, 52 - power, 16, power, 256, 256);
        }

        if(this.be.isOn) guiGraphics.blit(TEXTURE, this.leftPos + 79, this.topPos + 61, 192, 16, 35, 14, 256, 256);
        if(this.be.wasOn) guiGraphics.blit(TEXTURE, this.leftPos + 89, this.topPos + 42, 192, 0, 16, 16, 256, 256);

        this.be.tank.renderTank(this.leftPos + 35, this.topPos + 69, 0F, 16, 52);
    }

    @Override
    public boolean mouseClicked(double mouseX, double mouseY, int button) {
        if(button == 0 && this.isHovered(mouseX, mouseY, 89, 61, 16, 14)) {
            this.click();
            CompoundTag tag = new CompoundTag();
            tag.putBoolean("turnOn", true);
            PacketDistributor.sendToServer(new CompoundTagControl(tag, this.be.getBlockPos()));
            return true;
        }

        return super.mouseClicked(mouseX, mouseY, button);
    }
}
