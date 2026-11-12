package com.hbm.inventory.screens;

import api.hbm.energymk2.IEnergyReceiverMK2.ConnectionPriority;
import com.hbm.blockentity.network.FlowControlPumpBlockEntity;
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
 * Settings of the flow control pump (original GUIPump.java:20-112): the buffer size, a pressure button cycling 0 to 5 PU and a
 * priority button cycling through the priorities. Nothing is sent until the screen closes; the server clamps every value.
 */
public class FlowControlPumpScreen extends Screen {

    protected final FlowControlPumpBlockEntity pump;

    private EditBox textBuffer;
    private int pressure;
    private int priority;

    public FlowControlPumpScreen(FlowControlPumpBlockEntity pump) {
        super(Component.translatable(pump.getBlockState().getBlock().getDescriptionId()));
        this.pump = pump;
        this.pressure = pump.tank[0].getPressure();
        this.priority = pump.priority.ordinal();
    }

    @Override
    protected void init() {
        this.textBuffer = new EditBox(this.font, this.width / 2 - 150, 100, 90, 20, Component.empty());
        this.textBuffer.setMaxLength(5);
        this.textBuffer.setValue("" + this.pump.bufferSize);
        this.addRenderableWidget(this.textBuffer);

        this.addRenderableWidget(Button.builder(pressureLabel(), button -> {
            this.pressure++;
            if(this.pressure > FlowControlPumpBlockEntity.MAX_PRESSURE) this.pressure = 0;
            button.setMessage(pressureLabel());
        }).bounds(this.width / 2 - 50, 100, 90, 20).build());

        this.addRenderableWidget(Button.builder(priorityLabel(), button -> {
            this.priority++;
            if(this.priority >= ConnectionPriority.values().length) this.priority = 0;
            button.setMessage(priorityLabel());
        }).bounds(this.width / 2 + 50, 100, 90, 20).build());
    }

    private Component pressureLabel() {
        return Component.translatable("gui.hbmsntm.flow_control_pump.pu", this.pressure);
    }

    private Component priorityLabel() {
        return Component.literal(EnumUtil.<ConnectionPriority>grabEnumSafely(ConnectionPriority.class, this.priority).name());
    }

    @Override
    public void render(GuiGraphics guiGraphics, int mouseX, int mouseY, float partialTick) {
        super.render(guiGraphics, mouseX, mouseY, partialTick);
        guiGraphics.drawString(this.font, Component.translatable("gui.hbmsntm.network_control.throughput"), this.width / 2 - 150, 80, 0xA0A0A0);
        guiGraphics.drawString(this.font, Component.translatable("gui.hbmsntm.flow_control_pump.max"), this.width / 2 - 150, 90, 0xA0A0A0);
        guiGraphics.drawString(this.font, Component.translatable("gui.hbmsntm.flow_control_pump.pressure"), this.width / 2 - 50, 80, 0xA0A0A0);
        guiGraphics.drawString(this.font, Component.translatable("gui.hbmsntm.network_control.priority"), this.width / 2 + 50, 80, 0xA0A0A0);
    }

    /** The inventory key closes the screen unless the text field takes it (GUIPump.java:81-89). */
    @Override
    public boolean keyPressed(int keyCode, int scanCode, int modifiers) {
        if(super.keyPressed(keyCode, scanCode, modifiers)) return true;
        if(this.textBuffer.isFocused()) return false;
        if(this.minecraft != null && this.minecraft.options.keyInventory.matches(keyCode, scanCode)) {
            this.onClose();
            return true;
        }
        return false;
    }

    /** Sends the settings when the screen closes; a buffer that is not a number is left out (GUIPump.java:67-79). */
    @Override
    public void removed() {
        CompoundTag tag = new CompoundTag();
        tag.putByte("pressure", (byte) this.pressure);
        tag.putByte("priority", (byte) this.priority);
        try { tag.putInt("capacity", Integer.parseInt(this.textBuffer.getValue())); } catch(NumberFormatException ignored) { }
        PacketDistributor.sendToServer(new CompoundTagControl(tag, this.pump.getBlockPos()));
        super.removed();
    }

    @Override public boolean isPauseScreen() { return false; }
}
