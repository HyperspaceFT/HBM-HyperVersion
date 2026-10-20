package com.hbm.inventory.screens;

import com.hbm.blockentity.machine.rbmk.RBMKRodBlockEntity;
import com.hbm.inventory.menus.RBMKRodMenu;
import com.hbm.items.machine.RBMKRodItem;
import com.hbm.main.NuclearTechMod;
import com.hbm.util.i18n.I18nUtil;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.item.ItemStack;

import java.util.ArrayList;
import java.util.List;

/**
 * Original GUIRBMKRod: depletion and xenon bars of the loaded rod and the two hull temperature warnings. The warnings are hard-coded
 * English in the original (:33, :35); NEO uses the local keys container.rbmkRod.autoloaderHot / manualHot.
 */
public class RBMKRodScreen extends InfoScreen<RBMKRodMenu> {

    private static final ResourceLocation TEXTURE = NuclearTechMod.withDefaultNamespace("textures/gui/reactors/gui_rbmk_element.png");

    private final RBMKRodBlockEntity be;

    public RBMKRodScreen(RBMKRodMenu menu, Inventory playerInventory, Component title) {
        super(menu, playerInventory, title);

        this.be = menu.be;

        this.imageWidth = 176;
        this.imageHeight = 186;
    }

    @Override
    protected void init() {
        super.init();

        this.titleLabelX = this.imageWidth / 2 - this.font.width(this.title) / 2;
        this.titleLabelY = 6;
        this.inventoryLabelX = 8;
        this.inventoryLabelY = this.imageHeight - 96 + 2;
    }

    @Override
    public void render(GuiGraphics guiGraphics, int mouseX, int mouseY, float partialTicks) {
        super.render(guiGraphics, mouseX, mouseY, partialTicks);

        if(!be.coldEnoughForAutoloader())
            this.drawCustomInfoStat(guiGraphics, mouseX, mouseY, this.leftPos - 16, this.topPos + 20, 16, 16, this.leftPos - 8, this.topPos + 20 + 16, lines("container.rbmkRod.autoloaderHot"));
        if(!be.coldEnoughForManual())
            this.drawCustomInfoStat(guiGraphics, mouseX, mouseY, this.leftPos - 16, this.topPos + 36, 16, 16, this.leftPos - 8, this.topPos + 36 + 16, lines("container.rbmkRod.manualHot"));

        this.renderTooltip(guiGraphics, mouseX, mouseY);
    }

    private static List<Component> lines(String key) {
        List<Component> text = new ArrayList<>();
        for(String s : I18nUtil.resolveKeyArray(key)) text.add(Component.literal(s));
        return text;
    }

    @Override
    protected void renderBg(GuiGraphics guiGraphics, float partialTicks, int mouseX, int mouseY) {
        guiGraphics.blit(TEXTURE, this.leftPos, this.topPos, 0, 0, imageWidth, imageHeight);

        ItemStack stack = be.slots.get(0);
        if(stack.getItem() instanceof RBMKRodItem) {
            guiGraphics.blit(TEXTURE, this.leftPos + 34, this.topPos + 21, 176, 0, 18, 67);

            double depletion = 1D - RBMKRodItem.getEnrichment(stack);
            int d = (int)(depletion * 67);
            guiGraphics.blit(TEXTURE, this.leftPos + 34, this.topPos + 21, 194, 0, 18, d);

            double xenon = RBMKRodItem.getPoisonLevel(stack);
            int x = (int)(xenon * 58);
            guiGraphics.blit(TEXTURE, this.leftPos + 126, this.topPos + 82 - x, 212, 58 - x, 14, x);
        }

        if(!be.coldEnoughForAutoloader()) this.drawInfoPanel(guiGraphics, this.leftPos - 16, this.topPos + 20, 6);
        if(!be.coldEnoughForManual()) this.drawInfoPanel(guiGraphics, this.leftPos - 16, this.topPos + 36, 7);
    }
}
