package com.hbm.inventory.screens;

import com.hbm.blockentity.machine.oil.MachineCokerBlockEntity;
import com.hbm.handler.CokerRecipeClientSync;
import com.hbm.inventory.menus.MachineCokerMenu;
import com.hbm.main.NuclearTechMod;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.item.ItemStack;

public class MachineCokerScreen extends InfoScreen<MachineCokerMenu> {

    private static final ResourceLocation TEXTURE = NuclearTechMod.withDefaultNamespace("textures/gui/processing/gui_coker.png");
    private final MachineCokerBlockEntity be;

    public MachineCokerScreen(MachineCokerMenu menu, Inventory inventory, Component title) {
        super(menu, inventory, title);
        this.be = menu.be;
        this.imageWidth = 176;
        this.imageHeight = 204;
    }

    private Component status() {
        if(this.be.wasOn) return Component.translatable("machine_coker.status.running");
        var recipe = CokerRecipeClientSync.getRecipes().get(this.be.tanks[0].getTankType());
        if(recipe == null) return Component.translatable("machine_coker.status.recipe");
        if(this.be.tanks[0].getFill() < recipe.inputAmount()) return Component.translatable("machine_coker.status.input");
        ItemStack output = recipe.itemOutput();
        ItemStack stored = this.be.getItem(MachineCokerBlockEntity.SLOT_OUTPUT);
        var fluid = recipe.byproduct();
        boolean blockedItem = output != null && !output.isEmpty() &&
                ((!stored.isEmpty() && !ItemStack.isSameItemSameComponents(stored, output)) ||
                        (long) stored.getCount() + output.getCount() > Math.min(this.be.getMaxStackSize(), output.getMaxStackSize()));
        // Do not call canProcess here: the server's original processing order may change the byproduct type.
        boolean blockedFluid = fluid != null && (fluid.fill > this.be.tanks[1].getMaxFill() ||
                (this.be.tanks[1].getTankType() == fluid.type && (long)this.be.tanks[1].getFill() + fluid.fill > this.be.tanks[1].getMaxFill()));
        if(blockedItem || blockedFluid) return Component.translatable("machine_coker.status.output");
        return Component.translatable(this.be.heat < 100 ? "machine_coker.status.heat" : "machine_coker.status.waiting");
    }

    @Override public void render(GuiGraphics graphics, int mouseX, int mouseY, float partialTicks) {
        super.render(graphics, mouseX, mouseY, partialTicks);
        this.be.tanks[0].renderTankTooltip(graphics, mouseX, mouseY, this.leftPos + 35, this.topPos + 18, 16, 52);
        this.be.tanks[1].renderTankTooltip(graphics, mouseX, mouseY, this.leftPos + 125, this.topPos + 18, 16, 52);
        this.drawCustomInfoStat(graphics, mouseX, mouseY, this.leftPos + 60, this.topPos + 45, 54, 7, mouseX, mouseY,
                Component.translatable("machine_coker.progress", this.be.progress, MachineCokerBlockEntity.PROCESS_TIME),
                Component.translatable("machine_coker.warning.progress"));
        this.drawCustomInfoStat(graphics, mouseX, mouseY, this.leftPos + 60, this.topPos + 54, 54, 7, mouseX, mouseY,
                Component.translatable("machine_coker.heat", this.be.heat, MachineCokerBlockEntity.MAX_HEAT));
        this.drawCustomInfoStat(graphics, mouseX, mouseY, this.leftPos + 35, this.topPos + 72, 16, 16, mouseX, mouseY,
                Component.translatable("machine_coker.role.identifier"));
        this.drawCustomInfoStat(graphics, mouseX, mouseY, this.leftPos + 97, this.topPos + 27, 16, 16, mouseX, mouseY,
                Component.translatable("machine_coker.role.item_output"));
        this.drawInfoPanel(graphics, this.leftPos - 8, this.topPos + 18, 7);
        this.drawCustomInfoStat(graphics, mouseX, mouseY, this.leftPos - 8, this.topPos + 18, 16, 16, mouseX, mouseY,
                this.status(), Component.translatable("machine_coker.role.input"), Component.translatable("machine_coker.role.byproduct"),
                Component.translatable("machine_coker.warning.byproduct"), Component.translatable("machine_coker.config"));
        this.renderTooltip(graphics, mouseX, mouseY);
    }

    @Override protected void renderLabels(GuiGraphics graphics, int mouseX, int mouseY) {
        graphics.drawString(this.font, this.title, (this.imageWidth - this.font.width(this.title)) / 2, 6, 0xC7C1A3, false);
        graphics.drawString(this.font, this.playerInventoryTitle, 8, this.imageHeight - 96 + 2, 4210752, false);
    }

    @Override protected void renderBg(GuiGraphics graphics, float partialTicks, int mouseX, int mouseY) {
        graphics.blit(TEXTURE, this.leftPos, this.topPos, 0, 0, this.imageWidth, this.imageHeight, 256, 256);
        int progress = (int)Math.max(0L, Math.min(53L, (long)this.be.progress * 53 / MachineCokerBlockEntity.PROCESS_TIME));
        int heat = (int)Math.max(0L, Math.min(52L, (long)this.be.heat * 52 / MachineCokerBlockEntity.MAX_HEAT));
        if(progress > 0) graphics.blit(TEXTURE, this.leftPos + 61, this.topPos + 46, 176, 0, progress, 5, 256, 256);
        if(heat > 0) graphics.blit(TEXTURE, this.leftPos + 61, this.topPos + 55, 176, 5, heat, 5, 256, 256);
        this.be.tanks[0].renderTank(this.leftPos + 35, this.topPos + 70, 0F, 16, 52);
        this.be.tanks[1].renderTank(this.leftPos + 125, this.topPos + 70, 0F, 16, 52);
    }
}
