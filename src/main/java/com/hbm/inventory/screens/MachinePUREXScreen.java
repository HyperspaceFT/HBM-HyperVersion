package com.hbm.inventory.screens;

import com.hbm.blockentity.machine.MachinePUREXBlockEntity;
import com.hbm.inventory.menus.MachinePUREXMenu;
import com.hbm.inventory.recipes.PUREXRecipes;
import com.hbm.inventory.recipes.loader.GenericRecipe;
import com.hbm.items.NtmItems;
import com.hbm.items.machine.BlueprintsItem;
import com.hbm.main.NuclearTechMod;
import com.mojang.blaze3d.systems.RenderSystem;
import net.minecraft.ChatFormatting;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.inventory.Slot;
import net.minecraft.world.item.ItemStack;

/** Original GUIMachinePUREX.java. */
public class MachinePUREXScreen extends InfoScreen<MachinePUREXMenu> {

    private static final ResourceLocation TEXTURE = NuclearTechMod.withDefaultNamespace("textures/gui/processing/gui_purex.png");

    private final MachinePUREXBlockEntity be;

    public MachinePUREXScreen(MachinePUREXMenu menu, Inventory inventory, Component title) {
        super(menu, inventory, title);
        this.be = menu.be;
        this.imageWidth = 176;
        this.imageHeight = 256;
    }

    @Override
    public void render(GuiGraphics guiGraphics, int mouseX, int mouseY, float partialTicks) {
        super.render(guiGraphics, mouseX, mouseY, partialTicks);

        for(int i = 0; i < 3; i++) {
            this.be.inputTanks[i].renderTankTooltip(guiGraphics, mouseX, mouseY, this.leftPos + 8 + i * 18, this.topPos + 18, 16, 52);
        }
        this.be.outputTanks[0].renderTankTooltip(guiGraphics, mouseX, mouseY, this.leftPos + 116, this.topPos + 36, 16, 52);

        this.drawElectricityInfo(guiGraphics, mouseX, mouseY, this.leftPos + 152, this.topPos + 18, 16, 61, this.be.power, this.be.maxPower);

        if(this.isHovered(mouseX, mouseY, 7, 125, 18, 18)) {
            if(this.be.purexModule.recipe != null && PUREXRecipes.INSTANCE.recipeNameMap.containsKey(this.be.purexModule.recipe)) {
                GenericRecipe recipe = PUREXRecipes.INSTANCE.recipeNameMap.get(this.be.purexModule.recipe);
                guiGraphics.renderComponentTooltip(this.font, recipe.print(), mouseX, mouseY);
            } else {
                guiGraphics.renderTooltip(this.font, Component.translatable("container.recipe.set_recipe").withStyle(ChatFormatting.YELLOW), mouseX, mouseY);
            }
        }

        this.renderTooltip(guiGraphics, mouseX, mouseY);
    }

    @Override
    public boolean mouseClicked(double mouseX, double mouseY, int button) {
        if(this.isHovered(mouseX, mouseY, 7, 125, 18, 18)) {
            RecipeSelectorScreen.openSelector(PUREXRecipes.INSTANCE, this.be, this.be.purexModule.recipe, 0, BlueprintsItem.grabPool(this.be.slots.get(1)), this);
        }
        return super.mouseClicked(mouseX, mouseY, button);
    }

    @Override
    protected void renderLabels(GuiGraphics guiGraphics, int mouseX, int mouseY) {
        guiGraphics.drawString(this.font, this.title, 70 - this.font.width(this.title) / 2, 6, 4210752, false);
        guiGraphics.drawString(this.font, this.playerInventoryTitle, 8, this.imageHeight - 96 + 2, 4210752, false);
    }

    @Override
    protected void renderBg(GuiGraphics guiGraphics, float partialTicks, int mouseX, int mouseY) {
        guiGraphics.blit(TEXTURE, this.leftPos, this.topPos, 0, 0, this.imageWidth, this.imageHeight);

        int p = (int) (this.be.power * 61 / Math.max(this.be.maxPower, 1L));
        guiGraphics.blit(TEXTURE, this.leftPos + 152, this.topPos + 79 - p, 176, 61 - p, 16, p);

        if(this.be.purexModule.progress > 0) {
            int j = (int) Math.ceil(70D * this.be.purexModule.progress);
            guiGraphics.blit(TEXTURE, this.leftPos + 62, this.topPos + 126, 176, 61, j, 16);
        }

        GenericRecipe recipe = PUREXRecipes.INSTANCE.recipeNameMap.get(this.be.purexModule.recipe);

        if(this.be.didProcess) {
            guiGraphics.blit(TEXTURE, this.leftPos + 51, this.topPos + 121, 195, 0, 3, 6);
        } else if(recipe != null) {
            guiGraphics.blit(TEXTURE, this.leftPos + 51, this.topPos + 121, 192, 0, 3, 6);
        }

        if(this.be.didProcess) {
            guiGraphics.blit(TEXTURE, this.leftPos + 56, this.topPos + 121, 195, 0, 3, 6);
        } else if(recipe != null && this.be.power >= recipe.power) {
            guiGraphics.blit(TEXTURE, this.leftPos + 56, this.topPos + 121, 192, 0, 3, 6);
        }

        guiGraphics.renderItem(recipe != null ? recipe.getIcon() : new ItemStack(NtmItems.TEMPLATE_FOLDER.get()), this.leftPos + 8, this.topPos + 126);

        if(recipe != null && recipe.inputItem != null) {
            RenderSystem.setShaderColor(1F, 1F, 1F, 0.5F);
            for(int i = 0; i < Math.min(recipe.inputItem.length, this.be.purexModule.inputSlots.length); i++) {
                Slot slot = this.menu.slots.get(this.be.purexModule.inputSlots[i]);
                if(!slot.hasItem()) {
                    guiGraphics.renderItem(recipe.inputItem[i].extractForCyclingDisplay(20), this.leftPos + slot.x, this.topPos + slot.y);
                }
            }
            RenderSystem.setShaderColor(1F, 1F, 1F, 1F);
        }

        for(int i = 0; i < 3; i++) {
            this.be.inputTanks[i].renderTank(this.leftPos + 8 + i * 18, this.topPos + 70, 1F, 16, 52);
        }
        this.be.outputTanks[0].renderTank(this.leftPos + 116, this.topPos + 88, 1F, 16, 52);
    }
}
