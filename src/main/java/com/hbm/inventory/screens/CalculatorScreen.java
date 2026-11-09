package com.hbm.inventory.screens;

import com.hbm.util.Calculator;
import com.hbm.util.Tuple.Pair;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.gui.components.EditBox;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.network.chat.Component;
import org.lwjgl.glfw.GLFW;

import java.math.BigDecimal;
import java.math.MathContext;
import java.util.*;

public class CalculatorScreen extends Screen {
    private int xSize = 220;
    private int ySize = 50;
    private final int borderWidth = 2;
    private EditBox inputBox;

    private int selectedHist = -1;
    private static final int maxHistory = 6;
    private static final Deque<Pair<String, Double>> history = new ArrayDeque<>();
    private String latestResult = "?";

    public CalculatorScreen() {
        super(Component.empty());
    }

    @Override
    protected void init() {
        int x = (width - xSize) / 2;
        int y = (height - ySize) / 2;

        inputBox = new EditBox(this.font, x + 5, y + 8, 210, 13, Component.empty());
        inputBox.setCanLoseFocus(false);
        inputBox.setFocused(true);
        inputBox.setMaxLength(1000);
    }

    @Override
    public boolean keyPressed(int keyCode, int scanCode, int modifiers) {

        boolean b = inputBox.keyPressed(keyCode, scanCode, modifiers);

        if (keyCode == 257 || keyCode == 335) {
            String input = regexInput(inputBox.getValue());

            if (selectedHist != -1) {
                input = new ArrayList<>(history).get(selectedHist).key;
                inputBox.setValue(input);
            } else {
                try {
                    double result = Calculator.evaluateExpression(input);
                    history.addFirst(new Pair<>(input, result));
                    if (history.size() > maxHistory) history.removeLast();
                    String plainStringRepresentation = new BigDecimal(result, MathContext.DECIMAL64).toPlainString();
                    Minecraft.getInstance().keyboardHandler.setClipboard(plainStringRepresentation);
                    inputBox.setValue(plainStringRepresentation);
                    inputBox.moveCursorToEnd(false);
                    inputBox.setHighlightPos(0);
                } catch (Exception ignored) {
                }
                return true;
            }
        }

        if (keyCode == GLFW.GLFW_KEY_UP) { // up arrow
            selectedHist = Math.max(selectedHist - 1, -1);
        } else if (keyCode == GLFW.GLFW_KEY_DOWN) { // down arrow
            selectedHist = Math.min(selectedHist + 1, history.size() - 1);
        } else {
            selectedHist = -1;
        }

        this.update();

        return b || super.keyPressed(keyCode, scanCode, modifiers);
    }

    @Override
    public boolean charTyped(char codePoint, int modifiers) {
        if (inputBox.charTyped(codePoint, modifiers)) {
            this.update();
            return true;
        }
        return super.charTyped(codePoint, modifiers);
    }

    private void update() {
        String input = regexInput(inputBox.getValue());

        if (input.isEmpty()) {
            latestResult = "?";
            return;
        }
        try {
            latestResult = Double.toString(Calculator.evaluateExpression(input));
        } catch (Exception e) { latestResult = e.getClass().getName(); }
    }

    private static String regexInput(String s) {
        return s.replaceAll("[^\\d+\\-*/%^!.()\\sA-Za-z]+", "");
    }

    @Override
    public void render(GuiGraphics guiGraphics, int mouseX, int mouseY, float partialTicks) {
        guiGraphics.fillGradient(0, 0, this.width, this.height, -1072689136, -804253680);

        int x = (width - xSize) / 2;
        int y = (height - ySize) / 2;
        int histHeight = (font.lineHeight + 2) * maxHistory;
        int histStart = y + 30 + font.lineHeight + 8;

        guiGraphics.fill(x, y, x+xSize, y+ySize+histHeight, 0xFF2d2d2d);
        guiGraphics.fill(x+borderWidth, y+borderWidth, x+xSize-borderWidth, y+ySize-borderWidth+histHeight, 0xFF3d3d3d);
        guiGraphics.fill(x, histStart - 5, x+xSize, histStart - 3, 0xFF2d2d2d);

        inputBox.render(guiGraphics, mouseX, mouseY, partialTicks);
        guiGraphics.drawString(font, "=" + latestResult, x + 5, y + 30, -1);

        int i = 0;
        for (Pair<String, Double> prevInput : history) {
            int hy = y + 50 + (font.lineHeight+1)*i;
            if (i == selectedHist) {
                guiGraphics.fill(x + 4, hy - 1, x + 4 + xSize - 9, hy + font.lineHeight, 0xFF111111);
            }
            guiGraphics.drawString(font, prevInput.key + " = " + prevInput.value, x + 5, hy, -1);
            i++;
        }
    }
}
