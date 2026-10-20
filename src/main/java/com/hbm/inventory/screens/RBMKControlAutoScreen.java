package com.hbm.inventory.screens;

import com.hbm.blockentity.machine.rbmk.RBMKControlAutoBlockEntity;
import com.hbm.inventory.menus.RBMKControlAutoMenu;
import com.hbm.main.NuclearTechMod;
import com.hbm.network.toserver.CompoundTagControl;
import com.hbm.util.i18n.I18nUtil;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.gui.components.EditBox;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.player.Inventory;
import net.neoforged.neoforge.network.PacketDistributor;
import org.apache.commons.lang3.math.NumberUtils;
import org.lwjgl.glfw.GLFW;

import java.util.ArrayList;
import java.util.List;

/**
 * Original GUIRBMKControlAuto: the four parameter fields (level at max heat, level at min heat, max heat, min heat), the save button
 * and the three function buttons. The tooltips are hard-coded English in the original (:72-89); NEO uses the local keys
 * container.rbmkControlAuto.*. The power widget (:68-70, :163-165) belongs to the ReaSim control rods and is not ported.
 */
public class RBMKControlAutoScreen extends InfoScreen<RBMKControlAutoMenu> {

    private static final ResourceLocation TEXTURE = NuclearTechMod.withDefaultNamespace("textures/gui/reactors/gui_rbmk_control_auto.png");

    private final RBMKControlAutoBlockEntity be;

    private final EditBox[] fields = new EditBox[4];

    public RBMKControlAutoScreen(RBMKControlAutoMenu menu, Inventory playerInventory, Component title) {
        super(menu, playerInventory, title);

        this.be = menu.be;

        this.imageWidth = 176;
        this.imageHeight = 186;
    }

    @Override
    protected void init() {
        super.init();

        for(int i = 0; i < 4; i++) {
            // 26 x 6 as the original; an unbordered EditBox draws its text at its top, as GuiTextField does.
            this.fields[i] = new EditBox(this.font, this.leftPos + 30, this.topPos + 27 + 11 * i, 26, 6, Component.empty());
            this.fields[i].setTextColor(-1);
            this.fields[i].setTextColorUneditable(-1);
            this.fields[i].setBordered(false);

            if(i < 2)
                this.fields[i].setMaxLength(3);
            else
                this.fields[i].setMaxLength(4);
        }

        this.fields[0].setValue(String.valueOf((int)be.levelUpper));
        this.fields[1].setValue(String.valueOf((int)be.levelLower));
        this.fields[2].setValue(String.valueOf((int)be.heatUpper));
        this.fields[3].setValue(String.valueOf((int)be.heatLower));
    }

    @Override
    public void render(GuiGraphics guiGraphics, int mouseX, int mouseY, float partialTicks) {
        super.render(guiGraphics, mouseX, mouseY, partialTicks);

        this.drawCustomInfoStat(guiGraphics, mouseX, mouseY, this.leftPos + 124, this.topPos + 29, 16, 56, mouseX, mouseY, Component.literal((int)(be.level * 100) + "%"));

        String func = switch(be.function) {
            case LINEAR -> "container.rbmkControlAuto.linear";
            case QUAD_UP -> "container.rbmkControlAuto.quadUp";
            case QUAD_DOWN -> "container.rbmkControlAuto.quadDown";
        };

        this.drawCustomInfoStat(guiGraphics, mouseX, mouseY, this.leftPos + 58, this.topPos + 26, 28, 19, mouseX, mouseY, lines("container.rbmkControlAuto.function", I18nUtil.resolveKey(func)));
        this.drawCustomInfoStat(guiGraphics, mouseX, mouseY, this.leftPos + 61, this.topPos + 48, 22, 10, mouseX, mouseY, lines("container.rbmkControlAuto.selectLinear"));
        this.drawCustomInfoStat(guiGraphics, mouseX, mouseY, this.leftPos + 61, this.topPos + 59, 22, 10, mouseX, mouseY, lines("container.rbmkControlAuto.selectQuadUp"));
        this.drawCustomInfoStat(guiGraphics, mouseX, mouseY, this.leftPos + 61, this.topPos + 70, 22, 10, mouseX, mouseY, lines("container.rbmkControlAuto.selectQuadDown"));

        this.drawCustomInfoStat(guiGraphics, mouseX, mouseY, this.leftPos + 28, this.topPos + 26, 30, 10, mouseX, mouseY, lines("container.rbmkControlAuto.levelUpper"));
        this.drawCustomInfoStat(guiGraphics, mouseX, mouseY, this.leftPos + 28, this.topPos + 37, 30, 10, mouseX, mouseY, lines("container.rbmkControlAuto.levelLower"));
        this.drawCustomInfoStat(guiGraphics, mouseX, mouseY, this.leftPos + 28, this.topPos + 48, 30, 10, mouseX, mouseY, lines("container.rbmkControlAuto.heatUpper"));
        this.drawCustomInfoStat(guiGraphics, mouseX, mouseY, this.leftPos + 28, this.topPos + 59, 30, 10, mouseX, mouseY, lines("container.rbmkControlAuto.heatLower"));
        this.drawCustomInfoStat(guiGraphics, mouseX, mouseY, this.leftPos + 28, this.topPos + 70, 30, 10, mouseX, mouseY, lines("container.rbmkControlAuto.save"));

        this.renderTooltip(guiGraphics, mouseX, mouseY);
    }

    private static List<Component> lines(String key, Object... args) {
        List<Component> text = new ArrayList<>();
        for(String s : I18nUtil.resolveKeyArray(key, args)) text.add(Component.literal(s));
        return text;
    }

    /**
     * Original mouseClicked (:92-139). The fields and buttons are checked first: the container screen consumes every click inside
     * the GUI. As the original GuiTextField, a field is focused by a click on it and loses the focus on a click elsewhere.
     */
    @Override
    public boolean mouseClicked(double x, double y, int button) {

        boolean handled = false;

        for(EditBox field : this.fields) {
            boolean over = field.isMouseOver(x, y);
            field.setFocused(over);
            if(over) handled |= field.mouseClicked(x, y, button);
        }

        if(handled) return true;
        if(button != GLFW.GLFW_MOUSE_BUTTON_LEFT) return super.mouseClicked(x, y, button);

        if(leftPos + 28 <= x && leftPos + 28 + 30 > x && topPos + 70 < y && topPos + 70 + 10 >= y) {

            this.click();
            CompoundTag data = new CompoundTag();

            double[] vals = new double[] {0D ,0D, 0D, 0D};

            for(int k = 0; k < 4; k++) {

                double clamp = k < 2 ? 100 : 9999;
                double parsed = Double.NaN;

                // NEO: isNumber also accepts forms like "0x1" that parseDouble rejects; the original crashes the client there.
                if(NumberUtils.isNumber(fields[k].getValue())) {
                    try { parsed = Double.parseDouble(fields[k].getValue()); } catch(NumberFormatException ignored) { }
                }

                if(!Double.isNaN(parsed)) {
                    int j = (int) Mth.clamp(parsed, 0, clamp);
                    fields[k].setValue(j + "");
                    vals[k] = j;
                } else {
                    fields[k].setValue("0");
                }
            }

            data.putDouble("levelUpper", vals[0]);
            data.putDouble("levelLower", vals[1]);
            data.putDouble("heatUpper", vals[2]);
            data.putDouble("heatLower", vals[3]);

            PacketDistributor.sendToServer(new CompoundTagControl(data, be.getBlockPos()));
            return true;
        }

        for(int k = 0; k < 3; k++) {

            //manual rod control
            if(leftPos + 61 <= x && leftPos + 61 + 22 > x && topPos + 48 + k * 11 < y && topPos + 48 + 10 + k * 11 >= y) {

                this.click();
                CompoundTag data = new CompoundTag();
                data.putInt("function", k);
                PacketDistributor.sendToServer(new CompoundTagControl(data, be.getBlockPos()));
                return true;
            }
        }

        return super.mouseClicked(x, y, button);
    }

    @Override
    protected void renderLabels(GuiGraphics guiGraphics, int mouseX, int mouseY) {
        guiGraphics.drawString(this.font, this.title, this.imageWidth / 2 - this.font.width(this.title) / 2, 6, 4210752, false);
        guiGraphics.drawString(this.font, this.playerInventoryTitle, 8, this.imageHeight - 96 + 2, 4210752, false);
    }

    @Override
    protected void renderBg(GuiGraphics guiGraphics, float partialTicks, int mouseX, int mouseY) {
        guiGraphics.blit(TEXTURE, this.leftPos, this.topPos, 0, 0, this.imageWidth, this.imageHeight);

        int height = (int)(56 * (1D - be.level));

        if(height > 0)
            guiGraphics.blit(TEXTURE, this.leftPos + 124, this.topPos + 29, 176, 56 - height, 8, height);

        int f = be.function.ordinal();
        guiGraphics.blit(TEXTURE, this.leftPos + 59, this.topPos + 27, 184, f * 19, 26, 19);

        for(EditBox field : this.fields) {
            field.render(guiGraphics, mouseX, mouseY, partialTicks);
        }
    }

    // Original keyTyped (:172-181). A focused field keeps every key, so typing never closes the screen on the inventory key; escape still does.
    @Override
    public boolean keyPressed(int keyCode, int scanCode, int modifiers) {
        if(keyCode == GLFW.GLFW_KEY_ESCAPE) return super.keyPressed(keyCode, scanCode, modifiers);

        for(EditBox field : this.fields) {
            if(field.keyPressed(keyCode, scanCode, modifiers)) return true;
            if(field.canConsumeInput()) return true;
        }

        return super.keyPressed(keyCode, scanCode, modifiers);
    }

    @Override
    public boolean charTyped(char codePoint, int modifiers) {
        for(EditBox field : this.fields) {
            if(field.charTyped(codePoint, modifiers)) return true;
        }

        return super.charTyped(codePoint, modifiers);
    }
}
