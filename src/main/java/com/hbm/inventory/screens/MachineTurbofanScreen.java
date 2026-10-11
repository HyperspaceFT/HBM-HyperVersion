package com.hbm.inventory.screens;

import com.hbm.blockentity.machine.MachineTurbofanBlockEntity;
import com.hbm.inventory.menus.MachineTurbofanMenu;
import com.hbm.main.NuclearTechMod;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.player.Inventory;

public class MachineTurbofanScreen extends InfoScreen<MachineTurbofanMenu> {

    private static final ResourceLocation TEXTURE = NuclearTechMod.withDefaultNamespace("textures/gui/generators/gui_turbofan.png");
    private static final ResourceLocation BLOOD_GAUGE = NuclearTechMod.withDefaultNamespace("textures/gui/gauges/small_round.png");
    private final MachineTurbofanBlockEntity be;
    private static final String[] SLOT_NAMES = { "fuel", "empty", "afterburner", "battery", "identifier" };

    public MachineTurbofanScreen(MachineTurbofanMenu menu, Inventory inventory, Component title) {
        super(menu, inventory, title);
        this.be = menu.be;
        this.imageWidth = 176;
        this.imageHeight = 203;
    }
    @Override public void render(GuiGraphics graphics, int mouseX, int mouseY, float partialTicks) {
        super.render(graphics, mouseX, mouseY, partialTicks);
        this.be.tank.renderTankTooltip(graphics, mouseX, mouseY, this.leftPos + 35, this.topPos + 17, 34, 52);
        this.drawElectricityInfo(graphics, mouseX, mouseY, this.leftPos + 143, this.topPos + 17, 16, 52, this.be.power, MachineTurbofanBlockEntity.MAX_POWER);
        if(this.be.showBlood) this.drawCustomInfoStat(graphics, mouseX, mouseY, this.leftPos + 97, this.topPos + 16, 18, 18,
                Component.translatable("machine_turbofan.blood", this.be.blood.getFill(), MachineTurbofanBlockEntity.TANK_CAPACITY));
        for(int i = 0; i < 5; i++) {
            net.minecraft.world.inventory.Slot slot = this.menu.getSlot(i);
            if(!slot.hasItem()) this.drawCustomInfoStat(graphics, mouseX, mouseY, this.leftPos + slot.x, this.topPos + slot.y, 16, 16,
                    Component.translatable("machine_turbofan.slot." + SLOT_NAMES[i]));
        }
        this.drawInfoPanel(graphics, this.leftPos - 8, this.topPos + 36, 2);
        this.drawCustomInfoStat(graphics, mouseX, mouseY, this.leftPos - 8, this.topPos + 36, 16, 16,
                Component.translatable(this.be.redstonePowered ? "machine_turbofan.status.redstone" : this.be.wasOn ? "machine_turbofan.status.running" : "machine_turbofan.status.idle"),
                Component.translatable("machine_turbofan.afterburner", this.be.afterburner),
                Component.translatable("machine_turbofan.fuel_rate", this.be.consumption),
                Component.translatable("machine_turbofan.output", this.be.output),
                Component.translatable("machine_turbofan.warning.full"),
                Component.translatable("machine_turbofan.warning.charge_order"));
        this.drawInfoPanel(graphics, this.leftPos - 8, this.topPos + 68, 7);
        this.drawCustomInfoStat(graphics, mouseX, mouseY, this.leftPos - 8, this.topPos + 68, 16, 16,
                Component.translatable("machine_turbofan.warning.hazard"), Component.translatable("machine_turbofan.warning.redstone"),
                Component.translatable("machine_turbofan.warning.smoke"));
        if(MachineTurbofanBlockEntity.getBurnValue(this.be.tank.getTankType()) <= 0) {
            this.drawInfoPanel(graphics, this.leftPos - 8, this.topPos + 84, 6);
            this.drawCustomInfoStat(graphics, mouseX, mouseY, this.leftPos - 8, this.topPos + 84, 16, 16,
                    Component.translatable("machine_turbofan.warning.unsupported_fuel"));
        }
        this.drawCustomInfoStat(graphics, mouseX, mouseY, this.leftPos + 44, this.topPos + 71, 16, 16,
                Component.translatable("machine_turbofan.warning.type"));
        this.renderTooltip(graphics, mouseX, mouseY);
    }
    @Override protected void renderLabels(GuiGraphics graphics, int mouseX, int mouseY) {
        graphics.drawString(this.font, this.title, 43 - this.font.width(this.title) / 2, 6, 4210752, false);
        graphics.drawString(this.font, this.playerInventoryTitle, 8, this.imageHeight - 96 + 2, 4210752, false);
    }
    @Override protected void renderBg(GuiGraphics graphics, float partialTicks, int mouseX, int mouseY) {
        graphics.blit(TEXTURE, this.leftPos, this.topPos, 0, 0, this.imageWidth, this.imageHeight, 256, 256);
        int power = (int)Math.max(0L, Math.min(52L, this.be.getPowerScaled(52)));
        if(power > 0) graphics.blit(TEXTURE, this.leftPos + 143, this.topPos + 69 - power, 192, 52 - power, 16, power, 256, 256);
        if(this.be.afterburner > 0) graphics.blit(TEXTURE, this.leftPos + 98, this.topPos + 44, 176, (this.be.afterburner - 1) * 16, 16, 16, 256, 256);
        if(this.be.showBlood) {
            int frame = (int)Math.round(12D * this.be.blood.getFill() / MachineTurbofanBlockEntity.TANK_CAPACITY);
            graphics.blit(BLOOD_GAUGE, this.leftPos + 97, this.topPos + 16, 0, Mth.clamp(frame, 0, 12) * 18, 18, 18, 18, 234);
        }
        this.be.tank.renderTank(this.leftPos + 35, this.topPos + 69, 0F, 34, 52);
    }
}
