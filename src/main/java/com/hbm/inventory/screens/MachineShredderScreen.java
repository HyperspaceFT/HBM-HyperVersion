package com.hbm.inventory.screens;

import com.hbm.blockentity.machine.MachineShredderBlockEntity;
import com.hbm.inventory.menus.MachineShredderMenu;
import com.hbm.main.NuclearTechMod;
import net.minecraft.ChatFormatting;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.item.ItemStack;

import java.util.List;

public class MachineShredderScreen extends InfoScreen<MachineShredderMenu> {

    private static final ResourceLocation TEXTURE = NuclearTechMod.withDefaultNamespace("textures/gui/gui_shredder.png");

    private final MachineShredderBlockEntity be;

    public MachineShredderScreen(MachineShredderMenu menu, Inventory inventory, Component title) {
        super(menu, inventory, title);
        this.be = menu.be;
        this.imageWidth = 176;
        this.imageHeight = 233;
    }

    @Override
    public void render(GuiGraphics guiGraphics, int mouseX, int mouseY, float partialTicks) {
        super.render(guiGraphics, mouseX, mouseY, partialTicks);

        this.drawElectricityInfo(guiGraphics, mouseX, mouseY, this.leftPos + 8, this.topPos + 18, 16, 88, this.be.getPower(), this.be.getMaxPower());

        this.drawCustomInfoStat(guiGraphics, mouseX, mouseY, this.leftPos - 16, this.topPos + 36, 16, 16, mouseX, mouseY, this.getStatusTooltip());
        this.drawCustomInfoStat(guiGraphics, mouseX, mouseY, this.leftPos + 63, this.topPos + 89, 35, 18, mouseX, mouseY,
                Component.translatable("container.machine_shredder.process_info").withStyle(ChatFormatting.GRAY));
        this.drawCustomInfoStat(guiGraphics, mouseX, mouseY, this.leftPos + 44, this.topPos + 127, 18, 7, mouseX, mouseY,
                this.getBladeTooltip(this.be.getItem(27)));
        this.drawCustomInfoStat(guiGraphics, mouseX, mouseY, this.leftPos + 80, this.topPos + 127, 18, 7, mouseX, mouseY,
                this.getBladeTooltip(this.be.getItem(28)));
        this.drawCustomInfoStat(guiGraphics, mouseX, mouseY, this.leftPos + 8, this.topPos + 127, 18, 7, mouseX, mouseY,
                Component.translatable("container.machine_shredder.battery_hint").withStyle(ChatFormatting.GRAY));
        this.drawCustomInfoStat(guiGraphics, mouseX, mouseY, this.leftPos + 44, this.topPos + 8, 54, 8, mouseX, mouseY,
                Component.translatable("container.machine_shredder.input_hint").withStyle(ChatFormatting.GRAY),
                Component.translatable("container.machine_shredder.raw_ore_hint").withStyle(ChatFormatting.YELLOW),
                Component.translatable("container.machine_shredder.jei.unknown_fallback").withStyle(ChatFormatting.GRAY));
        this.drawCustomInfoStat(guiGraphics, mouseX, mouseY, this.leftPos + 116, this.topPos + 8, 54, 8, mouseX, mouseY,
                Component.translatable("container.machine_shredder.output_hint").withStyle(ChatFormatting.GRAY));

        this.renderTooltip(guiGraphics, mouseX, mouseY);
    }

    @Override
    protected void renderLabels(GuiGraphics guiGraphics, int mouseX, int mouseY) {
        guiGraphics.drawString(this.font, Component.translatable("container.machine_shredder.label.input"), 44, 8, 4210752, false);
        guiGraphics.drawString(this.font, Component.translatable("container.machine_shredder.label.output"), 116, 8, 4210752, false);
        guiGraphics.drawString(this.font, Component.translatable("container.machine_shredder.label.battery"), 8, 127, 4210752, false);
        guiGraphics.drawString(this.font, Component.translatable("container.machine_shredder.label.blade_left"), 44, 127, 4210752, false);
        guiGraphics.drawString(this.font, Component.translatable("container.machine_shredder.label.blade_right"), 80, 127, 4210752, false);
        guiGraphics.drawString(this.font, this.playerInventoryTitle, 8, this.imageHeight - 96 + 2, 4210752, false);
    }

    @Override
    protected void renderBg(GuiGraphics guiGraphics, float partialTicks, int mouseX, int mouseY) {
        guiGraphics.blit(TEXTURE, this.leftPos, this.topPos, 0, 0, this.imageWidth, this.imageHeight);

        int p = this.be.getPowerScaled(88);
        if(p > 0) {
            guiGraphics.blit(TEXTURE, this.leftPos + 8, this.topPos + 106 - p, 176, 160 - p, 16, p);
        }

        int progress = this.be.getProgressScaled(34);
        guiGraphics.blit(TEXTURE, this.leftPos + 63, this.topPos + 89, 176, 54, progress + 1, 18);

        int left = this.be.getGearLeft();
        int right = this.be.getGearRight();

        if(left != 0) {
            guiGraphics.blit(TEXTURE, this.leftPos + 43, this.topPos + 71, 176, (left - 1) * 18, 18, 18);
        }

        if(right != 0) {
            guiGraphics.blit(TEXTURE, this.leftPos + 79, this.topPos + 71, 194, (right - 1) * 18, 18, 18);
        }

        this.drawInfoPanel(guiGraphics, this.leftPos - 16, this.topPos + 36, this.getStatusIconType());
    }

    private int getStatusIconType() {
        return switch(this.be.getOperatingStatus()) {
            case MachineShredderBlockEntity.STATUS_RUNNING -> 1;
            case MachineShredderBlockEntity.STATUS_IDLE -> 5;
            default -> 6;
        };
    }

    private List<Component> getStatusTooltip() {
        ChatFormatting color = switch(this.be.getOperatingStatus()) {
            case MachineShredderBlockEntity.STATUS_RUNNING -> ChatFormatting.GREEN;
            case MachineShredderBlockEntity.STATUS_IDLE -> ChatFormatting.YELLOW;
            default -> ChatFormatting.RED;
        };
        String key = switch(this.be.getOperatingStatus()) {
            case MachineShredderBlockEntity.STATUS_RUNNING -> "container.machine_shredder.status.running";
            case MachineShredderBlockEntity.STATUS_MISSING_BLADES -> "container.machine_shredder.status.missing_blades";
            case MachineShredderBlockEntity.STATUS_BROKEN_BLADES -> "container.machine_shredder.status.broken_blades";
            case MachineShredderBlockEntity.STATUS_NO_POWER -> "container.machine_shredder.status.no_power";
            case MachineShredderBlockEntity.STATUS_OUTPUT_BLOCKED -> "container.machine_shredder.status.output_blocked";
            case MachineShredderBlockEntity.STATUS_INVALID_INPUT -> "container.machine_shredder.status.invalid_input";
            default -> "container.machine_shredder.status.idle";
        };
        return List.of(Component.translatable(key).withStyle(color));
    }

    private List<Component> getBladeTooltip(ItemStack stack) {
        if(stack.isEmpty()) {
            return List.of(Component.translatable("container.machine_shredder.blade_empty").withStyle(ChatFormatting.YELLOW));
        }
        if(stack.isDamageableItem()) {
            return List.of(Component.translatable("container.machine_shredder.blade_durability",
                    Math.max(0, stack.getMaxDamage() - stack.getDamageValue()), stack.getMaxDamage()).withStyle(ChatFormatting.GRAY));
        }
        return List.of(Component.translatable("container.machine_shredder.blade_durability_unlimited").withStyle(ChatFormatting.GRAY));
    }
}
