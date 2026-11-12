package com.hbm.inventory.screens;

import api.hbm.energymk2.IEnergyReceiverMK2.ConnectionPriority;
import com.hbm.blockentity.network.NetworkSeparatorBlockEntity;
import com.hbm.network.toserver.CompoundTagControl;
import com.hbm.util.EnumUtil;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.components.EditBox;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.neoforged.neoforge.network.PacketDistributor;

/**
 * Settings of the network separator (original GUIDiode.java:20-95): the throughput limit and a priority button cycling through the
 * priorities. Nothing is sent until the screen closes; the server clamps the limit.
 */
public class NetworkSeparatorScreen extends Screen {

    protected final NetworkSeparatorBlockEntity separator;

    private EditBox textThroughput;
    private int priority;

    public NetworkSeparatorScreen(NetworkSeparatorBlockEntity separator) {
        super(Component.translatable(separator.getBlockState().getBlock().getDescriptionId()));
        this.separator = separator;
        this.priority = separator.priority.ordinal();
    }

    @Override
    protected void init() {
        this.textThroughput = new EditBox(this.font, this.width / 2 - 150, 100, 90, 20, Component.empty());
        this.textThroughput.setMaxLength(11);
        this.textThroughput.setValue("" + this.separator.configuredLimit);
        this.addRenderableWidget(this.textThroughput);

        this.addRenderableWidget(Button.builder(priorityLabel(), button -> {
            this.priority++;
            if(this.priority >= ConnectionPriority.values().length) this.priority = 0;
            button.setMessage(priorityLabel());
        }).bounds(this.width / 2 + 20, 100, 90, 20).build());
    }

    private Component priorityLabel() {
        return Component.literal(EnumUtil.<ConnectionPriority>grabEnumSafely(ConnectionPriority.class, this.priority).name());
    }

    @Override
    public void render(GuiGraphics guiGraphics, int mouseX, int mouseY, float partialTick) {
        super.render(guiGraphics, mouseX, mouseY, partialTick);
        guiGraphics.drawString(this.font, Component.translatable("gui.hbmsntm.network_control.throughput"), this.width / 2 - 150, 80, 0xA0A0A0);
        guiGraphics.drawString(this.font, Component.translatable("gui.hbmsntm.network_separator.max"), this.width / 2 - 150, 90, 0xA0A0A0);
        guiGraphics.drawString(this.font, Component.translatable("gui.hbmsntm.network_control.priority"), this.width / 2 + 20, 80, 0xA0A0A0);
    }

    /** The inventory key closes the screen unless the text field takes it (GUIDiode.java:71-79). */
    @Override
    public boolean keyPressed(int keyCode, int scanCode, int modifiers) {
        if(super.keyPressed(keyCode, scanCode, modifiers)) return true;
        if(this.textThroughput.isFocused()) return false;
        if(this.minecraft != null && this.minecraft.options.keyInventory.matches(keyCode, scanCode)) {
            this.onClose();
            return true;
        }
        return false;
    }

    /** Sends the settings when the screen closes; a limit that is not a number is left out (GUIDiode.java:59-69). */
    @Override
    public void removed() {
        CompoundTag tag = new CompoundTag();
        tag.putByte("priority", (byte) this.priority);
        try { tag.putLong("limit", Long.parseLong(this.textThroughput.getValue())); } catch(NumberFormatException ignored) { }
        PacketDistributor.sendToServer(new CompoundTagControl(tag, this.separator.getBlockPos()));
        super.removed();
    }

    @Override public boolean isPauseScreen() { return false; }
}
