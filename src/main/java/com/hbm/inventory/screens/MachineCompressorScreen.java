package com.hbm.inventory.screens;

import com.hbm.blockentity.machine.MachineCompressorBlockEntity;
import com.hbm.handler.CompressorRecipeClientSync;
import com.hbm.inventory.menus.MachineCompressorMenu;
import com.hbm.inventory.recipes.CompressorRecipes.CompressorRecipe;
import com.hbm.main.NuclearTechMod;
import com.hbm.network.toserver.CompoundTagControl;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.player.Inventory;
import net.neoforged.neoforge.network.PacketDistributor;

public class MachineCompressorScreen extends InfoScreen<MachineCompressorMenu> {

    private static final ResourceLocation TEXTURE = NuclearTechMod.withDefaultNamespace("textures/gui/processing/gui_compressor.png");
    private final MachineCompressorBlockEntity be;

    public MachineCompressorScreen(MachineCompressorMenu menu, Inventory inventory, Component title) {
        super(menu, inventory, title);
        this.be = menu.be;
        this.imageWidth = 176;
        this.imageHeight = 204;
    }
    @Override public void render(GuiGraphics graphics, int mouseX, int mouseY, float partialTicks) {
        super.render(graphics, mouseX, mouseY, partialTicks);
        this.be.tanks[0].renderTankTooltip(graphics, mouseX, mouseY, this.leftPos + 17, this.topPos + 18, 16, 52);
        this.be.tanks[1].renderTankTooltip(graphics, mouseX, mouseY, this.leftPos + 107, this.topPos + 18, 16, 52);
        this.drawElectricityInfo(graphics, mouseX, mouseY, this.leftPos + 152, this.topPos + 18, 16, 52, this.be.power, MachineCompressorBlockEntity.MAX_POWER);
        for(int pressure = 0; pressure <= 4; pressure++) {
            // Display uses the server's received client snapshot, never the integrated server's processing map.
            CompressorRecipe recipe = CompressorRecipeClientSync.getRecipe(this.be.tanks[0].getTankType(), pressure);
            int output = recipe == null ? pressure + 1 : recipe.outputPressure();
            this.drawCustomInfoStat(graphics, mouseX, mouseY, this.leftPos + 43 + pressure * 11, this.topPos + 46, 8, 14, mouseX, mouseY,
                    Component.translatable("machine_compressor.pressure", pressure, output),
                    Component.translatable("machine_compressor.warning.settings"));
        }
        this.drawCustomInfoStat(graphics, mouseX, mouseY, this.leftPos + 42, this.topPos + 26, 55, 17, mouseX, mouseY,
                Component.translatable("machine_compressor.processing", this.be.processTime, this.be.powerRequirement),
                Component.translatable("machine_compressor.pressure", this.be.tanks[0].getPressure(), this.be.tanks[1].getPressure()),
                Component.translatable("machine_compressor.warning.power"));
        this.drawInfoPanel(graphics, this.leftPos - 8, this.topPos + 18, 7);
        this.drawCustomInfoStat(graphics, mouseX, mouseY, this.leftPos - 8, this.topPos + 18, 16, 16, mouseX, mouseY,
                Component.translatable("machine_compressor.warning.settings"), Component.translatable("machine_compressor.warning.pipes"));
        this.renderTooltip(graphics, mouseX, mouseY);
    }
    @Override protected void renderLabels(GuiGraphics graphics, int mouseX, int mouseY) {
        graphics.drawString(this.font, this.title, 70 - this.font.width(this.title) / 2, 6, 0xC7C1A3, false);
        graphics.drawString(this.font, this.playerInventoryTitle, 8, this.imageHeight - 96 + 2, 4210752, false);
    }
    @Override protected void renderBg(GuiGraphics graphics, float partialTicks, int mouseX, int mouseY) {
        graphics.blit(TEXTURE, this.leftPos, this.topPos, 0, 0, this.imageWidth, this.imageHeight, 256, 256);
        if(this.be.power > this.be.powerRequirement) graphics.blit(TEXTURE, this.leftPos + 156, this.topPos + 4, 176, 52, 9, 12, 256, 256);
        int pressure = Math.max(0, Math.min(4, this.be.tanks[0].getPressure()));
        graphics.blit(TEXTURE, this.leftPos + 43 + pressure * 11, this.topPos + 46, 193, 18, 8, 14, 256, 256);
        int progress = (int)Math.max(0L, Math.min(55L, (long)this.be.progress * 55 / Math.max(1, this.be.processTime)));
        if(progress > 0) graphics.blit(TEXTURE, this.leftPos + 42, this.topPos + 26, 192, 0, progress, 17, 256, 256);
        int power = (int)Math.max(0L, Math.min(52L, this.be.power * 52 / MachineCompressorBlockEntity.MAX_POWER));
        if(power > 0) graphics.blit(TEXTURE, this.leftPos + 152, this.topPos + 70 - power, 176, 52 - power, 16, power, 256, 256);
        this.be.tanks[0].renderTank(this.leftPos + 17, this.topPos + 70, 0F, 16, 52);
        this.be.tanks[1].renderTank(this.leftPos + 107, this.topPos + 70, 0F, 16, 52);
    }
    @Override public boolean mouseClicked(double mouseX, double mouseY, int button) {
        if(button == 0) for(int pressure = 0; pressure <= 4; pressure++) {
            if(this.isHovered(mouseX, mouseY, 43 + pressure * 11, 46, 8, 14)) {
                this.click();
                CompoundTag tag = new CompoundTag();
                tag.putInt("compression", pressure);
                PacketDistributor.sendToServer(new CompoundTagControl(tag, this.be.getBlockPos()));
                return true;
            }
        }
        return super.mouseClicked(mouseX, mouseY, button);
    }
}
