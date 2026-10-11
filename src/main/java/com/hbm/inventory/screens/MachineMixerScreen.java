package com.hbm.inventory.screens;

import com.hbm.blockentity.machine.MachineMixerBlockEntity;
import com.hbm.handler.MixerRecipeClientSync;
import com.hbm.inventory.FluidStack;
import com.hbm.inventory.menus.MachineMixerMenu;
import com.hbm.inventory.recipes.MixerRecipes.MixerRecipe;
import com.hbm.main.NuclearTechMod;
import com.hbm.network.toserver.CompoundTagControl;
import net.minecraft.ChatFormatting;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.item.ItemStack;
import net.neoforged.neoforge.network.PacketDistributor;

import java.util.ArrayList;
import java.util.List;

public class MachineMixerScreen extends InfoScreen<MachineMixerMenu> {

    private static final ResourceLocation TEXTURE = NuclearTechMod.withDefaultNamespace("textures/gui/processing/gui_mixer.png");
    private final MachineMixerBlockEntity be;

    public MachineMixerScreen(MachineMixerMenu menu, Inventory inventory, Component title) {
        super(menu, inventory, title);
        this.be = menu.be;
        this.imageWidth = 176;
        this.imageHeight = 204;
        menu.setClientSolidAcceptance(stack -> {
            MixerRecipe[] recipes = this.getRecipes();
            if(stack.isEmpty() || recipes.length == 0) return false;
            MixerRecipe recipe = recipes[Math.floorMod(this.be.recipeIndex, recipes.length)];
            return recipe.solidInput() != null && recipe.solidInput().matchesRecipe(stack, true);
        });
    }
    private MixerRecipe[] getRecipes() {
        MixerRecipe[] recipes = MixerRecipeClientSync.getRecipes().get(this.be.tanks[2].getTankType());
        return recipes == null ? new MixerRecipe[0] : recipes;
    }
    @Override public void render(GuiGraphics graphics, int mouseX, int mouseY, float partialTicks) {
        super.render(graphics, mouseX, mouseY, partialTicks);
        this.drawElectricityInfo(graphics, mouseX, mouseY, this.leftPos + 12, this.topPos + 18, 16, 52, this.be.power, MachineMixerBlockEntity.MAX_POWER);
        this.drawCustomInfoStat(graphics, mouseX, mouseY, this.leftPos + 152, this.topPos + 55, 8, 8, mouseX, mouseY,
                Component.translatable("container.upgrade"), Component.translatable("container.upgrade.speed"),
                Component.translatable("container.upgrade.power"), Component.translatable("container.upgrade.overdrive"));
        MixerRecipe[] recipes = this.getRecipes();
        List<Component> label = new ArrayList<>();
        if(recipes.length > 0) {
            int index = Math.floorMod(this.be.recipeIndex, recipes.length);
            MixerRecipe recipe = recipes[index];
            label.add(Component.translatable("machine_mixer.recipe", index + 1, recipes.length).withStyle(ChatFormatting.YELLOW));
            FluidStack first = recipe.input1();
            FluidStack second = recipe.input2();
            if(first != null) label.add(Component.translatable("machine_mixer.fluid_input", Component.translatable(first.type.getUnlocalizedName()), first.fill));
            if(second != null) label.add(Component.translatable("machine_mixer.fluid_input", Component.translatable(second.type.getUnlocalizedName()), second.fill));
            if(recipe.solidInput() != null) {
                List<ItemStack> choices = recipe.solidInput().extractForJEI();
                if(!choices.isEmpty()) {
                    long time = this.minecraft.level == null ? 0 : this.minecraft.level.getGameTime();
                    ItemStack stack = choices.get((int) ((time / 20) % choices.size()));
                    label.add(Component.translatable("machine_mixer.solid_input", stack.getHoverName(), recipe.solidInput().stacksize));
                }
            }
            if(recipes.length > 1) label.add(Component.translatable("machine_mixer.change_recipe").withStyle(ChatFormatting.RED));
        } else label.add(Component.translatable("machine_mixer.no_recipe"));
        label.add(Component.translatable(this.be.wasOn ? "machine_mixer.status.running" : "machine_mixer.status.waiting"));
        label.add(Component.translatable("machine_mixer.processing", this.be.processTime, this.be.consumption));
        label.add(Component.translatable("machine_mixer.warning.settings").withStyle(ChatFormatting.RED));
        this.drawCustomInfoStat(graphics, mouseX, mouseY, this.leftPos + 71, this.topPos + 17, 12, 12, mouseX, mouseY, label);
        this.be.tanks[0].renderTankTooltip(graphics, mouseX, mouseY, this.leftPos + 52, this.topPos + 18, 7, 52);
        this.be.tanks[1].renderTankTooltip(graphics, mouseX, mouseY, this.leftPos + 61, this.topPos + 18, 7, 52);
        this.be.tanks[2].renderTankTooltip(graphics, mouseX, mouseY, this.leftPos + 126, this.topPos + 18, 16, 52);
        this.drawInfoPanel(graphics, this.leftPos - 8, this.topPos + 18, 7);
        this.drawCustomInfoStat(graphics, mouseX, mouseY, this.leftPos - 8, this.topPos + 18, 16, 16, mouseX, mouseY,
                Component.translatable("machine_mixer.warning.settings"), Component.translatable("machine_mixer.warning.pipes"));
        this.renderTooltip(graphics, mouseX, mouseY);
    }
    @Override protected void renderLabels(GuiGraphics graphics, int mouseX, int mouseY) {
        graphics.drawString(this.font, this.title, 108 - this.font.width(this.title) / 2, 6, 4210752, false);
        graphics.drawString(this.font, this.playerInventoryTitle, 8, this.imageHeight - 96 + 2, 4210752, false);
    }
    @Override protected void renderBg(GuiGraphics graphics, float partialTicks, int mouseX, int mouseY) {
        graphics.blit(TEXTURE, this.leftPos, this.topPos, 0, 0, this.imageWidth, this.imageHeight, 256, 256);
        int power = (int) Math.max(0L, Math.min(52L, this.be.power * 52 / MachineMixerBlockEntity.MAX_POWER));
        if(power > 0) graphics.blit(TEXTURE, this.leftPos + 12, this.topPos + 70 - power, 176, 52 - power, 16, power, 256, 256);
        int progress = (int) Math.max(0L, Math.min(52L, (long) this.be.progress * 52 / Math.max(1, this.be.processTime)));
        if(progress > 0) graphics.blit(TEXTURE, this.leftPos + 71, this.topPos + 31, 192, 0, progress, 44, 256, 256);
        this.be.tanks[0].renderTank(this.leftPos + 52, this.topPos + 70, 0F, 7, 52);
        this.be.tanks[1].renderTank(this.leftPos + 61, this.topPos + 70, 0F, 7, 52);
        this.be.tanks[2].renderTank(this.leftPos + 126, this.topPos + 70, 0F, 16, 52);
        this.drawInfoPanel(graphics, this.leftPos + 152, this.topPos + 55, 8);
    }
    @Override public boolean mouseClicked(double mouseX, double mouseY, int button) {
        if(button == 0 && this.getRecipes().length > 1 && this.isHovered(mouseX, mouseY, 71, 17, 12, 12)) {
            this.click();
            CompoundTag tag = new CompoundTag();
            tag.putBoolean("toggle", true);
            PacketDistributor.sendToServer(new CompoundTagControl(tag, this.be.getBlockPos()));
            return true;
        }
        return super.mouseClicked(mouseX, mouseY, button);
    }
}
