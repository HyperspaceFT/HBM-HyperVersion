package com.hbm.inventory.screens;

import com.hbm.blockentity.machine.heater.HeaterOilburnerBlockEntity;
import com.hbm.inventory.menus.HeaterOilburnerMenu;
import com.hbm.main.NuclearTechMod;
import com.hbm.network.toserver.CompoundTagControl;
import com.hbm.inventory.fluid.trait.FT_Flammable;
import net.minecraft.ChatFormatting;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.player.Inventory;
import net.neoforged.neoforge.network.PacketDistributor;

import java.util.List;
import java.util.Locale;

public class HeaterOilburnerScreen extends InfoScreen<HeaterOilburnerMenu> {

    private static final ResourceLocation TEXTURE = NuclearTechMod.withDefaultNamespace("textures/gui/machine/gui_oilburner.png");

    private final HeaterOilburnerBlockEntity be;
    private boolean usingSlider;
    private int burnRate;

    public HeaterOilburnerScreen(HeaterOilburnerMenu menu, Inventory inventory, Component title) {
        super(menu, inventory, title);

        this.be = menu.be;
        this.burnRate = this.be.setting;
        this.imageWidth = 176;
        this.imageHeight = 203;
    }

    @Override
    public void render(GuiGraphics guiGraphics, int mouseX, int mouseY, float partialTicks) {
        // Follows the synced rate while the slider is not held, which also covers the original's reset when an overdrive
        // upgrade is removed and the cached rate is above the new maximum
        if(!this.usingSlider) this.burnRate = Mth.clamp(this.be.setting, 1, Math.max(this.be.maxBurnRate, 1));
        super.render(guiGraphics, mouseX, mouseY, partialTicks);

        this.drawCustomInfoStat(
                guiGraphics,
                mouseX,
                mouseY,
                this.leftPos + 116,
                this.topPos + 17,
                16,
                52,
                mouseX,
                mouseY,
                Component.literal(String.format(Locale.US, "%,d", this.be.heatEnergy) + " / " + String.format(Locale.US, "%,d", this.be.maxHeatEnergy) + " TU")
        );

        if(this.usingSlider || this.isHovered(mouseX, mouseY, 70, 23, 36, 8)) {
            guiGraphics.renderComponentTooltip(this.font, List.of(Component.literal(this.burnRate + " mB/t")),
                    Mth.clamp(mouseX, this.leftPos + 70, this.leftPos + 106), Mth.clamp(mouseY, this.topPos + 23, this.topPos + 31));
        }

        if(this.be.tank.getTankType().hasTrait(FT_Flammable.class)) {
            FT_Flammable trait = this.be.tank.getTankType().getTrait(FT_Flammable.class);
            int heat = (int) (trait.getHeatEnergy() * this.burnRate / 1000);
            this.drawCustomInfoStat(
                    guiGraphics,
                    mouseX,
                    mouseY,
                    this.leftPos + 79,
                    this.topPos + 34,
                    18,
                    18,
                    mouseX,
                    mouseY,
                    Component.literal(String.format(Locale.US, "%,d", heat) + " TU/t").withStyle(ChatFormatting.YELLOW),
                    Component.literal(String.format(Locale.US, "%,d", heat * 20) + " TU/s").withStyle(ChatFormatting.YELLOW)
            );
        }

        this.drawCustomInfoStat(guiGraphics, mouseX, mouseY, this.leftPos + 70, this.topPos + 54, 35, 15, mouseX, mouseY,
                Component.translatable("heater_oilburner.ignition"));

        this.be.tank.renderTankTooltip(guiGraphics, mouseX, mouseY, this.leftPos + 44, this.topPos + 17, 16, 52);

        this.renderTooltip(guiGraphics, mouseX, mouseY);
    }

    @Override
    protected void renderLabels(GuiGraphics guiGraphics, int mouseX, int mouseY) {
        guiGraphics.drawString(this.font, this.title, this.imageWidth / 2 - this.font.width(this.title) / 2, 6, 4210752, false);
        guiGraphics.drawString(this.font, this.playerInventoryTitle, 8, this.imageHeight - 96 + 2, 4210752, false);
    }

    @Override
    protected void renderBg(GuiGraphics guiGraphics, float partialTicks, int mouseX, int mouseY) {
        guiGraphics.blit(TEXTURE, this.leftPos, this.topPos, 0, 0, this.imageWidth, this.imageHeight);

        int heat = Math.min(this.be.heatEnergy * 52 / Math.max(this.be.maxHeatEnergy, 1), 52);
        guiGraphics.blit(TEXTURE, this.leftPos + 116, this.topPos + 69 - heat, 194, 52 - heat, 16, heat);

        int knob = Math.min((this.burnRate - 1) * 32 / Math.max(this.be.maxBurnRate - 1, 1), 32);
        guiGraphics.blit(TEXTURE, this.leftPos + 71 + knob, this.topPos + 23, 210, 14, 4, 8);

        if(this.be.isOn) {
            guiGraphics.blit(TEXTURE, this.leftPos + 70, this.topPos + 54, 210, 0, 35, 14);

            if(this.be.tank.getFill() > 0 && this.be.tank.getTankType().hasTrait(FT_Flammable.class)) {
                guiGraphics.blit(TEXTURE, this.leftPos + 79, this.topPos + 34, 176, 0, 18, 18);
            }
        }

        this.be.tank.renderTank(this.leftPos + 44, this.topPos + 69, 0, 16, 52);
    }

    @Override
    public boolean mouseClicked(double mouseX, double mouseY, int button) {
        if(this.isHovered(mouseX, mouseY, 80, 54, 16, 14)) {
            this.click();
            CompoundTag tag = new CompoundTag();
            tag.putBoolean("toggle", true);
            PacketDistributor.sendToServer(new CompoundTagControl(tag, this.be.getBlockPos()));
        }

        if(this.isHovered(mouseX, mouseY, 70, 23, 36, 8)) {
            this.click();
            this.usingSlider = true;
            this.updateBurnRate(mouseX);
            return true;
        }

        return super.mouseClicked(mouseX, mouseY, button);
    }

    @Override
    public boolean mouseDragged(double mouseX, double mouseY, int button, double dragX, double dragY) {
        if(this.usingSlider) {
            this.updateBurnRate(mouseX);
            return true;
        }
        return super.mouseDragged(mouseX, mouseY, button, dragX, dragY);
    }

    @Override
    public boolean mouseReleased(double mouseX, double mouseY, int button) {
        // Original: releasing the left or right button ends the drag
        if(this.usingSlider && (button == 0 || button == 1)) {
            this.updateBurnRate(mouseX);
            this.usingSlider = false;
            return true;
        }
        return super.mouseReleased(mouseX, mouseY, button);
    }

    private void updateBurnRate(double mouseX) {
        int maxBurnRate = Math.max(this.be.maxBurnRate, 1);
        int next = Mth.clamp(((int) mouseX - this.leftPos - 70) * maxBurnRate / 32, 1, maxBurnRate);
        if(next != this.burnRate) {
            this.burnRate = next;
            CompoundTag tag = new CompoundTag();
            tag.putInt("setting", next);
            PacketDistributor.sendToServer(new CompoundTagControl(tag, this.be.getBlockPos()));
        }
    }
}
