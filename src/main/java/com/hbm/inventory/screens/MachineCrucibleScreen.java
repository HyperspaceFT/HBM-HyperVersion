package com.hbm.inventory.screens;

import com.hbm.blockentity.machine.MachineCrucibleBlockEntity;
import com.hbm.inventory.material.Mats;
import com.hbm.inventory.menus.MachineCrucibleMenu;
import com.hbm.inventory.recipes.CrucibleRecipe;
import com.hbm.inventory.recipes.CrucibleRecipes;
import com.hbm.items.NtmItems;
import net.minecraft.ChatFormatting;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.network.chat.Component;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.item.ItemStack;

import java.util.ArrayList;
import java.util.List;

public class MachineCrucibleScreen extends InfoScreen<MachineCrucibleMenu> {

    private static final int BAR_X = 110, BAR_WIDTH = 52, BAR_HEIGHT = 9;
    private static final int HEAT_Y = 21, PROGRESS_Y = 35, RECIPE_STACK_Y = 49, WASTE_STACK_Y = 63;
    private static final int BUTTON_X = 16, BUTTON_Y = 35;
    /** Arrow between the input grid and the gauges; also the JEI recipe click area. */
    public static final int ARROW_X = 99, ARROW_Y = 37, ARROW_WIDTH = 10, ARROW_HEIGHT = 7;

    private final MachineCrucibleBlockEntity be;

    public MachineCrucibleScreen(MachineCrucibleMenu menu, Inventory inventory, Component title) {
        super(menu, inventory, title);
        this.be = menu.be;
        this.imageWidth = 176;
        this.imageHeight = 186;
    }

    @Override
    public void render(GuiGraphics graphics, int mouseX, int mouseY, float partialTicks) {
        super.render(graphics, mouseX, mouseY, partialTicks);
        this.drawCustomInfoStat(graphics, mouseX, mouseY, leftPos + BAR_X, topPos + HEAT_Y, BAR_WIDTH, BAR_HEIGHT, mouseX, mouseY,
                Component.translatable("container.machine_crucible.heat", be.heat, MachineCrucibleBlockEntity.MAX_HEAT),
                Component.translatable("container.machine_crucible.heat_requirement"));
        this.drawCustomInfoStat(graphics, mouseX, mouseY, leftPos + BAR_X, topPos + PROGRESS_Y, BAR_WIDTH, BAR_HEIGHT, mouseX, mouseY,
                Component.translatable("container.machine_crucible.progress", be.progress, MachineCrucibleBlockEntity.PROCESS_TIME),
                Component.translatable("container.machine_crucible.placement"));
        this.drawCustomInfoStat(graphics, mouseX, mouseY, leftPos + BAR_X, topPos + RECIPE_STACK_Y, BAR_WIDTH, BAR_HEIGHT, mouseX, mouseY,
                this.stackInfo("container.machine_crucible.recipe_stack", be.recipeStack, "container.machine_crucible.recipe_pour"));
        this.drawCustomInfoStat(graphics, mouseX, mouseY, leftPos + BAR_X, topPos + WASTE_STACK_Y, BAR_WIDTH, BAR_HEIGHT, mouseX, mouseY,
                this.stackInfo("container.machine_crucible.waste_stack", be.wasteStack, "container.machine_crucible.waste_pour"));

        if(this.isHovered(mouseX, mouseY, BUTTON_X, BUTTON_Y, 18, 18)) {
            CrucibleRecipe recipe = be.getLoadedRecipe();
            if(recipe != null) {
                graphics.renderComponentTooltip(this.font, recipe.print(), mouseX, mouseY);
            } else {
                graphics.renderComponentTooltip(this.font, List.of(
                        Component.translatable("container.recipe.set_recipe").withStyle(ChatFormatting.YELLOW),
                        Component.translatable("container.machine_crucible.select_recipe")), mouseX, mouseY);
            }
        }
        this.renderTooltip(graphics, mouseX, mouseY);
    }

    private List<Component> stackInfo(String header, List<Mats.MaterialStack> stacks, String pour) {
        List<Component> text = new ArrayList<>();
        text.add(Component.translatable(header, MachineCrucibleBlockEntity.getQuantaFromType(stacks, null),
                MachineCrucibleBlockEntity.CAPACITY));
        if(stacks.isEmpty()) text.add(Component.translatable("container.machine_crucible.empty").withStyle(ChatFormatting.RED));
        for(Mats.MaterialStack stack : stacks) {
            text.add(Component.translatable("container.machine_crucible.amount", stack.material.getName(), stack.amount)
                    .withStyle(ChatFormatting.YELLOW));
        }
        text.add(Component.translatable(pour));
        return text;
    }

    @Override
    public boolean mouseClicked(double mouseX, double mouseY, int button) {
        if(button == 0 && this.isHovered(mouseX, mouseY, BUTTON_X, BUTTON_Y, 18, 18)) {
            RecipeSelectorScreen.openSelector(CrucibleRecipes.INSTANCE, be, be.recipe, 0, null, this);
            return true;
        }
        return super.mouseClicked(mouseX, mouseY, button);
    }

    @Override
    protected void renderLabels(GuiGraphics graphics, int mouseX, int mouseY) {
        graphics.drawString(font, title, imageWidth / 2 - font.width(title) / 2, 6, 0x404040, false);
        graphics.drawString(font, playerInventoryTitle, 8, imageHeight - 96 + 2, 0x404040, false);
    }

    @Override
    protected void renderBg(GuiGraphics graphics, float partialTicks, int mouseX, int mouseY) {
        graphics.fill(leftPos, topPos, leftPos + imageWidth, topPos + imageHeight, 0xffc6c6c6);
        graphics.fill(leftPos + 4, topPos + 4, leftPos + imageWidth - 4, topPos + imageHeight - 4, 0xffdedede);
        for(int row = 0; row < 3; row++) {
            for(int col = 0; col < 3; col++) {
                int x = leftPos + 43 + col * 18;
                int y = topPos + 17 + row * 18;
                graphics.fill(x, y, x + 18, y + 18, 0xff777777);
                graphics.fill(x + 1, y + 1, x + 17, y + 17, 0xff373737);
            }
        }

        int buttonX = leftPos + BUTTON_X, buttonY = topPos + BUTTON_Y;
        graphics.fill(buttonX, buttonY, buttonX + 18, buttonY + 18, 0xff777777);
        graphics.fill(buttonX + 1, buttonY + 1, buttonX + 17, buttonY + 17, 0xff8b8b8b);
        CrucibleRecipe recipe = be.getLoadedRecipe();
        graphics.renderItem(recipe != null ? recipe.getIcon() : new ItemStack(NtmItems.TEMPLATE_FOLDER.get()), buttonX + 1, buttonY + 1);

        int arrowX = leftPos + ARROW_X, arrowY = topPos + ARROW_Y;
        graphics.fill(arrowX, arrowY + 2, arrowX + 6, arrowY + 5, 0xff777777);
        for(int i = 0; i < 4; i++) graphics.fill(arrowX + 6 + i, arrowY + i, arrowX + 7 + i, arrowY + ARROW_HEIGHT - i, 0xff777777);

        drawBar(graphics, HEAT_Y, be.heat, MachineCrucibleBlockEntity.MAX_HEAT, 0xffe87534);
        drawBar(graphics, PROGRESS_Y, be.progress, MachineCrucibleBlockEntity.PROCESS_TIME, 0xffcfb34c);
        drawStack(graphics, RECIPE_STACK_Y, be.recipeStack);
        drawStack(graphics, WASTE_STACK_Y, be.wasteStack);

        for(int row = 0; row < 3; row++) {
            for(int col = 0; col < 9; col++) {
                int x = leftPos + 7 + col * 18;
                int y = topPos + 103 + row * 18;
                graphics.fill(x, y, x + 18, y + 18, 0xff777777);
                graphics.fill(x + 1, y + 1, x + 17, y + 17, 0xff373737);
            }
        }
        for(int col = 0; col < 9; col++) {
            int x = leftPos + 7 + col * 18;
            int y = topPos + 161;
            graphics.fill(x, y, x + 18, y + 18, 0xff777777);
            graphics.fill(x + 1, y + 1, x + 17, y + 17, 0xff373737);
        }
    }

    private void drawBar(GuiGraphics graphics, int barY, int value, int maximum, int color) {
        int y = topPos + barY;
        graphics.fill(leftPos + BAR_X, y, leftPos + BAR_X + BAR_WIDTH, y + BAR_HEIGHT, 0xff666666);
        int width = Math.max(0, Math.min(BAR_WIDTH, value * BAR_WIDTH / Math.max(1, maximum)));
        if(width > 0) graphics.fill(leftPos + BAR_X, y, leftPos + BAR_X + width, y + BAR_HEIGHT, color);
    }

    /** One segment per material in its molten colour, like upstream's stacked crucible gauge. */
    private void drawStack(GuiGraphics graphics, int barY, List<Mats.MaterialStack> stacks) {
        int y = topPos + barY;
        graphics.fill(leftPos + BAR_X, y, leftPos + BAR_X + BAR_WIDTH, y + BAR_HEIGHT, 0xff666666);
        int quanta = 0, lastWidth = 0;
        for(Mats.MaterialStack stack : stacks) {
            quanta += stack.amount;
            int width = Math.min(BAR_WIDTH, (int) ((long) quanta * BAR_WIDTH / MachineCrucibleBlockEntity.CAPACITY));
            if(width > lastWidth) graphics.fill(leftPos + BAR_X + lastWidth, y, leftPos + BAR_X + width, y + BAR_HEIGHT,
                    0xff000000 | stack.material.moltenColor);
            lastWidth = Math.max(lastWidth, width);
        }
    }
}
