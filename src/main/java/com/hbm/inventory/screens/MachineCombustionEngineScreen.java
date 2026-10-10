package com.hbm.inventory.screens;

import com.hbm.blockentity.machine.MachineCombustionEngineBlockEntity;
import com.hbm.inventory.fluid.trait.FT_Combustible;
import com.hbm.inventory.menus.MachineCombustionEngineMenu;
import com.hbm.items.machine.PistonSetItem;
import com.hbm.main.NuclearTechMod;
import com.hbm.network.toserver.CompoundTagControl;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.player.Inventory;
import net.neoforged.neoforge.network.PacketDistributor;

import java.util.Locale;

public class MachineCombustionEngineScreen extends InfoScreen<MachineCombustionEngineMenu> {

    private static final ResourceLocation TEXTURE = NuclearTechMod.withDefaultNamespace("textures/gui/generators/gui_combustion.png");
    private final MachineCombustionEngineBlockEntity be;
    private boolean draggingThrottle;
    private int setting;

    public MachineCombustionEngineScreen(MachineCombustionEngineMenu menu, Inventory inventory, Component title) {
        super(menu, inventory, title);
        this.be = menu.be;
        this.setting = this.be.setting;
        this.imageWidth = 176;
        this.imageHeight = 203;
    }

    @Override
    public void render(GuiGraphics graphics, int mouseX, int mouseY, float partialTicks) {
        if(!this.draggingThrottle) this.setting = Mth.clamp(this.be.setting, 0, MachineCombustionEngineBlockEntity.MAX_SETTING);
        super.render(graphics, mouseX, mouseY, partialTicks);
        if(!this.draggingThrottle) {
            this.be.tank.renderTankTooltip(graphics, mouseX, mouseY, this.leftPos + 35, this.topPos + 17, 16, 52);
            this.drawElectricityInfo(graphics, mouseX, mouseY, this.leftPos + 143, this.topPos + 17, 16, 52, this.be.power, MachineCombustionEngineBlockEntity.MAX_POWER);
        }
        this.drawCustomInfoStat(graphics, mouseX, mouseY, this.leftPos + 79, this.topPos + 13, 35, 15, mouseX, mouseY,
                Component.translatable("machine_combustion_engine.action.toggle"),
                Component.translatable(this.be.isOn ? "machine_combustion_engine.status.on" : "machine_combustion_engine.status.off"),
                Component.translatable(this.be.wasOn ? "machine_combustion_engine.status.running" : "machine_combustion_engine.status.idle"));
        Component throttle = Component.translatable("machine_combustion_engine.throttle", this.setting);
        Component fuelRate = Component.translatable("machine_combustion_engine.fuel_rate", String.format(Locale.US, "%.1f", this.setting * 0.2D));
        if(this.draggingThrottle) {
            graphics.renderComponentTooltip(this.font, java.util.List.of(throttle, fuelRate),
                    Mth.clamp(mouseX, this.leftPos + 80, this.leftPos + 114), Mth.clamp(mouseY, this.topPos + 38, this.topPos + 46));
        } else {
            this.drawCustomInfoStat(graphics, mouseX, mouseY, this.leftPos + 79, this.topPos + 38, 36, 8, mouseX, mouseY, throttle, fuelRate);
        }
        PistonSetItem.Type piston = PistonSetItem.getType(this.be.getItem(2));
        if(piston != null) {
            long nominal = 0L;
            if(this.be.tank.getTankType().hasTrait(FT_Combustible.class)) {
                FT_Combustible fuel = this.be.tank.getTankType().getTrait(FT_Combustible.class);
                nominal = (long)(this.setting * 2 * (fuel.getCombustionEnergy() / 10000D) * this.be.getEfficiency());
            }
            this.drawCustomInfoStat(graphics, mouseX, mouseY, this.leftPos + 79, this.topPos + 50, 35, 14, mouseX, mouseY,
                    Component.translatable("machine_combustion_engine.output.tick", String.format(Locale.US, "%,d", nominal)),
                    Component.translatable("machine_combustion_engine.output.second", String.format(Locale.US, "%,d", nominal * 20L)),
                    Component.translatable("machine_combustion_engine.warning.tail"));
        }
        this.drawCustomInfoStat(graphics, mouseX, mouseY, this.leftPos + 143, this.topPos + 71, 16, 16, mouseX, mouseY,
                Component.translatable("machine_combustion_engine.charge_hint"));
        this.drawInfoPanel(graphics, this.leftPos - 8, this.topPos + 18, 7);
        this.drawCustomInfoStat(graphics, mouseX, mouseY, this.leftPos - 8, this.topPos + 18, 16, 16, mouseX, mouseY,
                Component.translatable("machine_combustion_engine.remainder", String.format(Locale.US, "%.1f", Mth.clamp(this.be.tenth, 0, 9) / 10D)),
                Component.translatable("machine_combustion_engine.warning.type"),
                Component.translatable("machine_combustion_engine.warning.full"));
        if(piston == null || this.be.getEfficiency() <= 0D) {
            this.drawInfoPanel(graphics, this.leftPos - 8, this.topPos + 50, 6);
            this.drawCustomInfoStat(graphics, mouseX, mouseY, this.leftPos - 8, this.topPos + 50, 16, 16, mouseX, mouseY,
                    Component.translatable(piston == null ? "machine_combustion_engine.warning.piston" : "machine_combustion_engine.warning.unsupported_fuel"));
        }
        this.renderTooltip(graphics, mouseX, mouseY);
    }

    @Override
    protected void renderLabels(GuiGraphics graphics, int mouseX, int mouseY) {
        graphics.drawString(this.font, this.playerInventoryTitle, 8, this.imageHeight - 96 + 2, 4210752, false);
    }

    @Override
    protected void renderBg(GuiGraphics graphics, float partialTicks, int mouseX, int mouseY) {
        graphics.blit(TEXTURE, this.leftPos, this.topPos, 0, 0, this.imageWidth, this.imageHeight, 256, 256);
        PistonSetItem.Type piston = PistonSetItem.getType(this.be.getItem(2));
        if(piston != null) graphics.blit(TEXTURE, this.leftPos + 80, this.topPos + 51, 176, 52 + piston.ordinal() * 12, 25, 12, 256, 256);
        graphics.blit(TEXTURE, this.leftPos + 79 + this.setting * 32 / 30, this.topPos + 38, 192, 15, 4, 8, 256, 256);
        if(this.be.isOn) graphics.blit(TEXTURE, this.leftPos + 79, this.topPos + 13, 192, 0, 35, 15, 256, 256);
        int power = (int)Math.max(0L, Math.min(52L, this.be.getPowerScaled(52L)));
        if(power > 0) graphics.blit(TEXTURE, this.leftPos + 143, this.topPos + 69 - power, 176, 52 - power, 16, power, 256, 256);
        this.be.tank.renderTank(this.leftPos + 35, this.topPos + 69, 0F, 16, 52);
    }

    @Override
    public boolean mouseClicked(double mouseX, double mouseY, int button) {
        if(button == 0 && this.isHovered(mouseX, mouseY, 89, 13, 16, 14)) {
            this.click();
            CompoundTag tag = new CompoundTag();
            tag.putBoolean("turnOn", true);
            PacketDistributor.sendToServer(new CompoundTagControl(tag, this.be.getBlockPos()));
            return true;
        }
        if(button == 0 && this.isHovered(mouseX, mouseY, 79, 38, 36, 8)) {
            this.click();
            this.draggingThrottle = true;
            this.updateThrottle(mouseX);
            return true;
        }
        return super.mouseClicked(mouseX, mouseY, button);
    }

    @Override
    public boolean mouseDragged(double mouseX, double mouseY, int button, double dragX, double dragY) {
        if(button == 0 && this.draggingThrottle) {
            this.updateThrottle(mouseX);
            return true;
        }
        return super.mouseDragged(mouseX, mouseY, button, dragX, dragY);
    }

    @Override
    public boolean mouseReleased(double mouseX, double mouseY, int button) {
        if(button == 0 && this.draggingThrottle) {
            this.updateThrottle(mouseX);
            this.draggingThrottle = false;
            return true;
        }
        return super.mouseReleased(mouseX, mouseY, button);
    }

    private void updateThrottle(double mouseX) {
        int next = Mth.clamp((int)((mouseX - this.leftPos - 81) * 30 / 32), 0, MachineCombustionEngineBlockEntity.MAX_SETTING);
        if(this.setting != next) {
            this.setting = next;
            CompoundTag tag = new CompoundTag();
            tag.putInt("setting", next);
            PacketDistributor.sendToServer(new CompoundTagControl(tag, this.be.getBlockPos()));
        }
    }
}
