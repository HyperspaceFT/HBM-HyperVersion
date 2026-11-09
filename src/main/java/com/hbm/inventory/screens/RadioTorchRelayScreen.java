package com.hbm.inventory.screens;

import com.hbm.blockentity.network.RadioTorchBaseBlockEntity;
import com.hbm.blockentity.network.RadioTorchRelayBlockEntity;
import com.hbm.main.NuclearTechMod;
import com.hbm.network.toserver.CompoundTagControl;
import com.mojang.blaze3d.platform.InputConstants;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.gui.components.EditBox;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.neoforged.neoforge.network.PacketDistributor;
import org.lwjgl.glfw.GLFW;

/** Screen of the RoR calculation relay. Original GUIScreenRadioTorchRelay.java */
public class RadioTorchRelayScreen extends Screen {

    protected static final ResourceLocation TEXTURE = NuclearTechMod.withDefaultNamespace("textures/gui/machine/gui_rtty_relay.png");
    protected final RadioTorchRelayBlockEntity radio;
    protected int imageWidth = 256;
    protected int imageHeight = 78;
    protected int leftPos;
    protected int topPos;

    protected EditBox frequency;
    protected EditBox expression;

    public RadioTorchRelayScreen(RadioTorchRelayBlockEntity radio) {
        super(Component.translatable("container.rtty_relay"));
        this.radio = radio;
    }

    @Override public boolean isPauseScreen() { return false; }

    @Override
    protected void init() {

        this.leftPos = (this.width - this.imageWidth) / 2;
        this.topPos = (this.height - this.imageHeight) / 2;

        int oX = 4;
        int oY = 4;

        this.frequency = new EditBox(this.font, this.leftPos + 25 + oX, this.topPos + 17 + oY, 90 - oX * 2, 14, Component.empty());
        this.frequency.setTextColor(0x00ff00);
        this.frequency.setTextColorUneditable(0x00ff00);
        this.frequency.setBordered(false);
        this.frequency.setMaxLength(RadioTorchBaseBlockEntity.MAX_CHAN_LENGTH);
        this.frequency.setValue(radio.channel == null ? "" : radio.channel);
        this.addRenderableWidget(this.frequency);

        this.expression = new EditBox(this.font, this.leftPos + 7 + oX, this.topPos + 53 + oY, 220 - oX * 2, 14, Component.empty());
        this.expression.setTextColor(0x00ff00);
        this.expression.setTextColorUneditable(0x00ff00);
        this.expression.setBordered(false);
        this.expression.setMaxLength(RadioTorchRelayBlockEntity.MAX_EXPRESSION_LENGTH);
        this.expression.setValue(radio.expression == null ? "" : radio.expression);
        this.addRenderableWidget(this.expression);
    }

    @Override
    public void render(GuiGraphics guiGraphics, int mouseX, int mouseY, float partialTick) {
        this.renderTransparentBackground(guiGraphics);
        this.renderBackground(guiGraphics, mouseX, mouseY, partialTick);
        this.renderLabels(guiGraphics, mouseX, mouseY);
    }

    @Override
    public void renderBackground(GuiGraphics guiGraphics, int mouseX, int mouseY, float partialTick) {
        guiGraphics.blit(TEXTURE, this.leftPos, this.topPos, 0, 0, this.imageWidth, this.imageHeight);
        if(radio.polling) guiGraphics.blit(TEXTURE, this.leftPos + 173, this.topPos + 17, 0, 78, 18, 18);

        this.frequency.render(guiGraphics, mouseX, mouseY, partialTick);
        this.expression.render(guiGraphics, mouseX, mouseY, partialTick);
    }

    protected void renderLabels(GuiGraphics guiGraphics, int mouseX, int mouseY) {
        guiGraphics.drawString(this.font, this.title, this.leftPos + this.imageWidth / 2 - this.font.width(this.title) / 2, this.topPos + 6, 4210752, false);

        if(ScreenUtils.isHovered(this.leftPos, this.topPos, mouseX, mouseY, 173, 17, 18, 18)) {
            guiGraphics.renderTooltip(this.font, Component.translatable(radio.polling ? "container.rtty.polling" : "container.rtty.change"), mouseX, mouseY);
        }
        if(ScreenUtils.isHovered(this.leftPos, this.topPos, mouseX, mouseY, 209, 17, 18, 18)) {
            guiGraphics.renderTooltip(this.font, Component.translatable("container.rtty.save"), mouseX, mouseY);
        }
    }

    @Override
    @SuppressWarnings("DataFlowIssue")
    public boolean mouseClicked(double mouseX, double mouseY, int button) {

        this.frequency.mouseClicked(mouseX, mouseY, button);
        this.expression.mouseClicked(mouseX, mouseY, button);

        if(ScreenUtils.isHovered(this.leftPos, this.topPos, mouseX, mouseY, 173, 17, 18, 18)) {
            ScreenUtils.click(this.minecraft);
            CompoundTag tag = new CompoundTag();
            tag.putBoolean("p", !radio.polling);
            PacketDistributor.sendToServer(new CompoundTagControl(tag, radio.getBlockPos()));
        }

        if(ScreenUtils.isHovered(this.leftPos, this.topPos, mouseX, mouseY, 209, 17, 18, 18)) {
            ScreenUtils.click(this.minecraft);
            CompoundTag tag = new CompoundTag();
            tag.putString("c", this.frequency.getValue());
            tag.putString("e", this.expression.getValue());
            PacketDistributor.sendToServer(new CompoundTagControl(tag, radio.getBlockPos()));
        }

        return super.mouseClicked(mouseX, mouseY, button);
    }

    @Override
    public boolean charTyped(char codePoint, int modifiers) {
        if(this.frequency.charTyped(codePoint, modifiers)) return true;
        if(this.expression.charTyped(codePoint, modifiers)) return true;
        return super.charTyped(codePoint, modifiers);
    }

    @Override
    @SuppressWarnings("DataFlowIssue")
    public boolean keyPressed(int keyCode, int scanCode, int modifiers) {

        if(this.frequency.keyPressed(keyCode, scanCode, modifiers)) return true;
        if(this.expression.keyPressed(keyCode, scanCode, modifiers)) return true;

        // original keyTyped (GUIScreenRadioTorchRelay.java:119): a focused text box takes every key, so typing never closes the screen on the inventory key
        if(keyCode != GLFW.GLFW_KEY_ESCAPE && (this.frequency.canConsumeInput() || this.expression.canConsumeInput())) return true;

        InputConstants.Key key = InputConstants.getKey(keyCode, scanCode);
        if(keyCode == GLFW.GLFW_KEY_ESCAPE || this.minecraft.options.keyInventory.isActiveAndMatches(key)) {
            this.onClose();
            return true;
        }

        return super.keyPressed(keyCode, scanCode, modifiers);
    }
}
