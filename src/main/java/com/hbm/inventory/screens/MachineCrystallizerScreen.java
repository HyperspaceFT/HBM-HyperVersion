package com.hbm.inventory.screens;

import com.hbm.blockentity.machine.MachineCrystallizerBlockEntity;
import com.hbm.handler.CrystallizerRecipeClientSync;
import com.hbm.inventory.menus.MachineCrystallizerMenu;
import com.hbm.inventory.recipes.CrystallizerRecipes.CrystallizerRecipe;
import com.hbm.items.machine.MachineUpgradeItem.UpgradeType;
import com.hbm.main.NuclearTechMod;
import net.minecraft.ChatFormatting;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.player.Inventory;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

public class MachineCrystallizerScreen extends InfoScreen<MachineCrystallizerMenu> {

    private static final ResourceLocation TEXTURE = NuclearTechMod.withDefaultNamespace("textures/gui/processing/gui_crystallizer_alt.png");
    private static final String[] SLOT_NAMES = { "input", "battery", "output", "fluid_in", "fluid_out", "upgrade", "upgrade", "identifier" };
    private final MachineCrystallizerBlockEntity be;

    public MachineCrystallizerScreen(MachineCrystallizerMenu menu, Inventory inventory, Component title) {
        super(menu, inventory, title);
        this.be = menu.be;
        this.imageWidth = 176;
        this.imageHeight = 204;
    }
    @Override public void render(GuiGraphics graphics, int mouseX, int mouseY, float partialTicks) {
        super.render(graphics, mouseX, mouseY, partialTicks);
        this.drawElectricityInfo(graphics, mouseX, mouseY, this.leftPos + 152, this.topPos + 18, 16, 52, this.be.power, MachineCrystallizerBlockEntity.MAX_POWER);
        this.be.tank.renderTankTooltip(graphics, mouseX, mouseY, this.leftPos + 35, this.topPos + 18, 16, 52);
        this.drawCustomInfoStat(graphics, mouseX, mouseY, this.leftPos + 117, this.topPos + 22, 8, 8, this.leftPos + 200, this.topPos + 45,
                Component.translatable("container.upgrade"), Component.translatable("container.upgrade.speed"),
                Component.translatable("container.upgrade.effectiveness"), Component.translatable("container.upgrade.overdrive"));
        for(int i = 0; i < 8; i++) {
            net.minecraft.world.inventory.Slot slot = this.menu.getSlot(i);
            if(!slot.hasItem()) this.drawCustomInfoStat(graphics, mouseX, mouseY, this.leftPos + slot.x, this.topPos + slot.y, 16, 16,
                    Component.translatable("machine_crystallizer.slot." + SLOT_NAMES[i]));
        }
        List<Component> status = new ArrayList<>();
        status.add(Component.translatable(this.be.isOn ? "machine_crystallizer.status.running" : "machine_crystallizer.status.idle"));
        status.add(Component.translatable("machine_crystallizer.progress", this.be.progress, this.be.duration, this.be.duration + 1));
        int speed = this.be.upgradeManager.getLevel(UpgradeType.SPEED);
        int effect = this.be.upgradeManager.getLevel(UpgradeType.EFFECT);
        int overdrive = this.be.upgradeManager.getLevel(UpgradeType.OVERDRIVE);
        status.add(Component.translatable("machine_crystallizer.consumption", MachineCrystallizerBlockEntity.getPowerRequired(speed, effect), MachineCrystallizerBlockEntity.getCycleCount(overdrive)));
        CrystallizerRecipe recipe = CrystallizerRecipeClientSync.getOutput(this.menu.getSlot(0).getItem(), this.be.tank.getTankType());
        if(recipe != null) {
            float chance = effect > 0 ? Math.min(effect * recipe.productivity, MachineCrystallizerBlockEntity.MAX_FREE_CHANCE) : 0F;
            status.add(Component.translatable("machine_crystallizer.chance", String.format(Locale.ROOT, "%.0f", chance * 100F)));
            status.add(Component.translatable("machine_crystallizer.acid", recipe.acidAmount(), Component.translatable(recipe.acidType().getUnlocalizedName())));
        } else status.add(Component.translatable("machine_crystallizer.no_recipe").withStyle(ChatFormatting.RED));
        this.drawInfoPanel(graphics, this.leftPos - 8, this.topPos + 36, 2);
        this.drawCustomInfoStat(graphics, mouseX, mouseY, this.leftPos - 8, this.topPos + 36, 16, 16, mouseX, mouseY, status);
        this.drawInfoPanel(graphics, this.leftPos - 8, this.topPos + 68, 7);
        this.drawCustomInfoStat(graphics, mouseX, mouseY, this.leftPos - 8, this.topPos + 68, 16, 16,
                Component.translatable("machine_crystallizer.warning.cycles"), Component.translatable("machine_crystallizer.warning.progress"),
                Component.translatable("machine_crystallizer.warning.acid"), Component.translatable("machine_crystallizer.warning.type"));
        this.renderTooltip(graphics, mouseX, mouseY);
    }
    @Override protected void renderLabels(GuiGraphics graphics, int mouseX, int mouseY) {
        graphics.drawString(this.font, this.title, 70 - this.font.width(this.title) / 2, 6, 4210752, false);
        graphics.drawString(this.font, this.playerInventoryTitle, 8, this.imageHeight - 96 + 2, 4210752, false);
    }
    @Override protected void renderBg(GuiGraphics graphics, float partialTicks, int mouseX, int mouseY) {
        graphics.blit(TEXTURE, this.leftPos, this.topPos, 0, 0, this.imageWidth, this.imageHeight, 256, 256);
        int power = (int) Math.max(0L, Math.min(52L, this.be.getPowerScaled(52)));
        if(power > 0) graphics.blit(TEXTURE, this.leftPos + 152, this.topPos + 70 - power, 176, 64 - power, 16, power, 256, 256);
        int progress = Math.max(0, Math.min(28, this.be.getProgressScaled(28)));
        if(progress > 0) graphics.blit(TEXTURE, this.leftPos + 80, this.topPos + 47, 176, 0, progress, 12, 256, 256);
        this.drawInfoPanel(graphics, this.leftPos + 117, this.topPos + 22, 8);
        this.be.tank.renderTank(this.leftPos + 35, this.topPos + 70, 0F, 16, 52);
    }
}
