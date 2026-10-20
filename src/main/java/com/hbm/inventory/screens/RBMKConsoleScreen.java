package com.hbm.inventory.screens;

import com.hbm.blockentity.machine.rbmk.RBMKColumnType;
import com.hbm.blockentity.machine.rbmk.RBMKConsoleBlockEntity;
import com.hbm.blockentity.machine.rbmk.RBMKConsoleBlockEntity.RBMKColumn;
import com.hbm.blockentity.machine.rbmk.RBMKControlManualBlockEntity.RBMKColor;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.menus.RBMKConsoleMenu;
import com.hbm.main.NuclearTechMod;
import com.hbm.network.toserver.CompoundTagControl;
import com.hbm.registry.NtmSoundEvents;
import com.hbm.util.i18n.I18nUtil;
import com.mojang.blaze3d.vertex.VertexConsumer;
import net.minecraft.ChatFormatting;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.gui.components.EditBox;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.resources.sounds.SimpleSoundInstance;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.player.Inventory;
import net.neoforged.neoforge.network.PacketDistributor;
import org.apache.commons.lang3.math.NumberUtils;
import org.joml.Matrix4f;
import org.lwjgl.glfw.GLFW;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

/**
 * Original GUIRBMKConsole: the 15 x 15 column grid, the flux graph, the six screen buttons, the selection, colour group and
 * compressor buttons, the rod level field and the AZ-5 button. The original is a plain GuiScreen; NEO opens it through the
 * slotless RBMKConsoleMenu and draws no title or inventory label, as the original draws none. The hard-coded English tooltips
 * (:95-111) and the column type names of the grid tooltip (:88) use the local keys rbmk.console.*.
 */
public class RBMKConsoleScreen extends InfoScreen<RBMKConsoleMenu> {

    private static final ResourceLocation TEXTURE = NuclearTechMod.withDefaultNamespace("textures/gui/reactors/gui_rbmk_console.png");

    private static final String[] GROUPS = new String[] {"red", "yellow", "green", "blue", "purple"};
    private static final ChatFormatting[] GROUP_COLORS = new ChatFormatting[] {ChatFormatting.RED, ChatFormatting.YELLOW, ChatFormatting.GREEN, ChatFormatting.BLUE, ChatFormatting.LIGHT_PURPLE};

    private final RBMKConsoleBlockEntity be;

    private boolean[] selection = new boolean[15 * 15];
    private boolean az5Lid = true;
    private long lastPress = 0;

    private EditBox field;

    public RBMKConsoleScreen(RBMKConsoleMenu menu, Inventory playerInventory, Component title) {
        super(menu, playerInventory, title);

        this.be = menu.be;

        this.imageWidth = 244;
        this.imageHeight = 172;
    }

    @Override
    protected void init() {
        super.init();

        // An unbordered EditBox draws its text at its top, as GuiTextField does.
        this.field = new EditBox(this.font, this.leftPos + 9, this.topPos + 84, 35, 9, Component.empty());
        this.field.setTextColor(0x00ff00);
        this.field.setTextColorUneditable(0x008000);
        this.field.setBordered(false);
        this.field.setMaxLength(3);
    }

    @Override
    public void render(GuiGraphics guiGraphics, int mouseX, int mouseY, float partialTicks) {
        super.render(guiGraphics, mouseX, mouseY, partialTicks);

        int bX = 86;
        int bY = 11;
        int size = 10;

        // NEO-only: the original's hover test reads guiTop + 11 + 10150 and index > 0, so the top-left column never shows its tooltip;
        // these are the bounds of the click handler.
        if(leftPos + 86 <= mouseX && leftPos + 86 + 150 > mouseX && topPos + 11 < mouseY && topPos + 11 + 150 >= mouseY) {
            int index = ((mouseX - bX - leftPos) / size + (mouseY - bY - topPos) / size * 15);

            if(index >= 0 && index < be.columns.length) {
                RBMKColumn col = be.columns[index];

                if(col != null) {

                    List<Component> list = new ArrayList<>();
                    list.add(Component.literal(I18nUtil.resolveKey("rbmk.console.type." + col.type.name().toLowerCase(Locale.US))));
                    list.addAll(getFancyStats(col));
                    guiGraphics.renderComponentTooltip(this.font, list, mouseX, mouseY);
                }
            }
        }

        this.drawCustomInfoStat(guiGraphics, mouseX, mouseY, leftPos + 61, topPos + 70, 10, 10, mouseX, mouseY, Component.literal(I18nUtil.resolveKey("rbmk.console.selectAll")));
        this.drawCustomInfoStat(guiGraphics, mouseX, mouseY, leftPos + 72, topPos + 70, 10, 10, mouseX, mouseY, Component.literal(I18nUtil.resolveKey("rbmk.console.deselectAll")));

        for(int i = 0; i < 3; i++) {
            for(int j = 0; j < 2; j++) {
                int id = i * 2 + j + 1;
                this.drawCustomInfoStat(guiGraphics, mouseX, mouseY, leftPos + 6 + 40 * j, topPos + 8 + 21 * i, 18, 18, mouseX, mouseY, Component.literal(I18nUtil.resolveKey("rbmk.console." + be.screens[id - 1].type.name().toLowerCase(Locale.US), id)).withStyle(ChatFormatting.YELLOW));
                this.drawCustomInfoStat(guiGraphics, mouseX, mouseY, leftPos + 24 + 40 * j, topPos + 8 + 21 * i, 18, 18, mouseX, mouseY, Component.literal(I18nUtil.resolveKey("rbmk.console.assign", id)));
            }
        }

        for(int k = 0; k < 5; k++) {
            this.drawCustomInfoStat(guiGraphics, mouseX, mouseY, leftPos + 6 + 11 * k, topPos + 70, 10, 10, mouseX, mouseY,
                    Component.literal(I18nUtil.resolveKey("rbmk.console.group." + GROUPS[k] + ".select")).withStyle(GROUP_COLORS[k]),
                    Component.literal(I18nUtil.resolveKey("rbmk.console.group." + GROUPS[k] + ".assign")).withStyle(GROUP_COLORS[k]));
        }

        this.drawCustomInfoStat(guiGraphics, mouseX, mouseY, leftPos + 70, topPos + 82, 12, 12, mouseX, mouseY, Component.literal(I18nUtil.resolveKey("rbmk.console.compressor")));
    }

    /**
     * Original RBMKColumn.getFancyStats (TileEntityRBMKConsole :444-499), the grid tooltip lines below the column type.
     */
    public static List<Component> getFancyStats(RBMKColumn column) {

        CompoundTag data = column.data;

        /*
         * Making a big switch with the values converted based on type by hand might seem "UnPrOfEsSiOnAl" and a major pain in the ass
         * but my only other solution that would not have me do things in multiple places where they shouldn't be involved passing
         * classes in the enum and then calling a special method from that class and quite honestly it turned out to be such a crime
         * against humanity that I threw the towel. It's not fancy, I get that, please fuck off.
         */

        List<Component> stats = new ArrayList<>();
        stats.add(line(ChatFormatting.YELLOW, I18nUtil.resolveKey("rbmk.heat", ((int)((data.getDouble("heat") * 10D)) / 10D) + "°C")));
        switch(column.type) {

            case FUEL:
            case FUEL_SIM:
                stats.add(line(ChatFormatting.GREEN, I18nUtil.resolveKey("rbmk.rod.depletion", ((int)(((1D - data.getDouble("enrichment")) * 100000)) / 1000D) + "%")));
                stats.add(line(ChatFormatting.DARK_PURPLE, I18nUtil.resolveKey("rbmk.rod.xenon", ((int)(((data.getDouble("xenon")) * 1000D)) / 1000D) + "%")));
                stats.add(line(ChatFormatting.DARK_RED, I18nUtil.resolveKey("rbmk.rod.coreTemp", ((int)((data.getDouble("c_coreHeat") * 10D)) / 10D) + "°C")));
                stats.add(line(ChatFormatting.RED, I18nUtil.resolveKey("rbmk.rod.skinTemp", ((int)((data.getDouble("c_heat") * 10D)) / 10D) + "°C", ((int)((data.getDouble("c_maxHeat") * 10D)) / 10D) + "°C")));
                break;
            case BOILER:
                stats.add(line(ChatFormatting.BLUE, I18nUtil.resolveKey("rbmk.boiler.water", data.getInt("water"), data.getInt("maxWater"))));
                stats.add(line(ChatFormatting.WHITE, I18nUtil.resolveKey("rbmk.boiler.steam", data.getInt("steam"), data.getInt("maxSteam"))));
                stats.add(line(ChatFormatting.YELLOW, I18nUtil.resolveKey("rbmk.boiler.type", Fluids.fromID(data.getShort("type")).getName().getString())));
                break;
            case CONTROL:

                if(data.contains("color")) {
                    short col = data.getShort("color");

                    if(col >= 0 && col < RBMKColor.values().length)
                        stats.add(line(ChatFormatting.YELLOW, I18nUtil.resolveKey("rbmk.control." + RBMKColor.values()[col].name().toLowerCase(Locale.US))));
                }

                // No break, as the original (upstream-shared): the manual rods also show the level line of CONTROL_AUTO.
            case CONTROL_AUTO:
                stats.add(line(ChatFormatting.YELLOW, I18nUtil.resolveKey("rbmk.control.level", ((int)((data.getDouble("level") * 100D))) + "%")));
                break;

            case HEATEX:
                stats.add(line(ChatFormatting.BLUE, Fluids.fromID(data.getShort("type")).getName().getString() + " " +
                        data.getInt("water") + "/" + data.getInt("maxWater") + "mB"));
                stats.add(line(ChatFormatting.RED, Fluids.fromID(data.getShort("hottype")).getName().getString() + " " +
                        data.getInt("steam") + "/" + data.getInt("maxSteam") + "mB"));
                break;
            default:
                break;
        }

        if(data.getBoolean("moderated"))
            stats.add(line(ChatFormatting.YELLOW, I18nUtil.resolveKey("rbmk.moderated")));

        return stats;
    }

    private static Component line(ChatFormatting color, String text) {
        return Component.literal(text).withStyle(color);
    }

    /** Original mouseClicked (:120-300): the early returns as the original; the compressor and save buttons fall through. Every mouse button counts. */
    @Override
    public boolean mouseClicked(double mouseX, double mouseY, int button) {

        boolean over = this.field.isMouseOver(mouseX, mouseY);
        this.field.setFocused(over);
        if(over) {
            this.field.mouseClicked(mouseX, mouseY, button);
            return true;
        }

        int LEFT_CLICK = GLFW.GLFW_MOUSE_BUTTON_LEFT;
        int RIGTH_CLICK = GLFW.GLFW_MOUSE_BUTTON_RIGHT;

        int bX = 86;
        int bY = 11;
        int size = 10;

        //toggle column selection
        if(leftPos + 86 <= mouseX && leftPos + 86 + 150 > mouseX && topPos + 11 < mouseY && topPos + 11 + 150 >= mouseY) {

            int index = (((int) mouseX - bX - leftPos) / size + ((int) mouseY - bY - topPos) / size * 15);

            if(index >= 0 && index < selection.length && be.columns[index] != null) {
                this.selection[index] = !this.selection[index];

                this.click(0.75F + (this.selection[index] ? 0.25F : 0.0F));
                return true;
            }
        }

        //clear selection
        if(leftPos + 72 <= mouseX && leftPos + 72 + 10 > mouseX && topPos + 70 < mouseY && topPos + 70 + 10 >= mouseY) {
            this.selection = new boolean[15 * 15];
            this.click(0.5F);
            return true;
        }

        //select all control rods
        if(leftPos + 61 <= mouseX && leftPos + 61 + 10 > mouseX && topPos + 70 < mouseY && topPos + 70 + 10 >= mouseY) {
            this.selection = new boolean[15 * 15];

            for(int j = 0; j < be.columns.length; j++) {

                if(be.columns[j] != null && be.columns[j].type == RBMKColumnType.CONTROL) {
                    this.selection[j] = true;
                }
            }
            this.click(1.5F);
            return true;
        }

        //compressor
        if(leftPos + 70 <= mouseX && leftPos + 70 + 12 > mouseX && topPos + 82 < mouseY && topPos + 82 + 12 >= mouseY) {
            CompoundTag control = new CompoundTag();
            control.putBoolean("compressor", true);
            control.putIntArray("cols", this.selectedOfType(RBMKColumnType.BOILER));
            this.send(control);
            this.click(1F);
        }

        //select color groups
        for(int k = 0; k < 5; k++) {

            if(leftPos + 6 + k * 11 <= mouseX && leftPos + 6 + k * 11 + 10 > mouseX && topPos + 70 < mouseY && topPos + 70 + 10 >= mouseY) {

                if(button == LEFT_CLICK) {
                    this.selection = new boolean[15 * 15];

                    for(int j = 0; j < be.columns.length; j++) {

                        if(be.columns[j] != null && be.columns[j].type == RBMKColumnType.CONTROL && be.columns[j].data.getShort("color") == k) {
                            this.selection[j] = true;
                        }
                    }
                }

                if(button == RIGTH_CLICK) {
                    CompoundTag control = new CompoundTag();
                    control.putByte("assignColor", (byte) k);
                    control.putIntArray("cols", this.selectedOfType(RBMKColumnType.CONTROL));
                    this.send(control);
                }

                this.click(0.8F + k * 0.1F);
                return true;
            }
        }

        //AZ-5
        if(leftPos + 30 <= mouseX && leftPos + 30 + 28 > mouseX && topPos + 138 < mouseY && topPos + 138 + 28 >= mouseY) {

            if(az5Lid) {
                az5Lid = false;
                this.play(NtmSoundEvents.RBMK_AZ5_COVER.get(), 0.5F);
            } else if(lastPress + 3000 < System.currentTimeMillis()) {
                // The shutdown sound plays on the clicking client only, as the original.
                this.play(NtmSoundEvents.SHUTDOWN.get(), 1F);
                lastPress = System.currentTimeMillis();

                this.send(RBMKConsoleBlockEntity.buildAZ5Control(be.columns));
                this.click(1F);
            }
            return true;
        }

        //save control rod setting
        if(leftPos + 48 <= mouseX && leftPos + 48 + 12 > mouseX && topPos + 82 < mouseY && topPos + 82 + 12 >= mouseY) {

            double level = Double.NaN;

            // NEO: isNumber also accepts forms like "0x1" that parseDouble rejects; the original crashes the client there.
            if(NumberUtils.isNumber(field.getValue())) {
                try { level = Double.parseDouble(field.getValue()); } catch(NumberFormatException ignored) { }
            }

            if(Double.isNaN(level)) return true;

            int j = (int) Mth.clamp(level, 0, 100);
            field.setValue(j + "");

            CompoundTag control = new CompoundTag();
            control.putDouble("level", j * 0.01D);

            for(int s = 0; s < selection.length; s++) {
                if(selection[s])
                    control.putInt("sel_" + s, s);
            }

            this.send(control);
            this.click(1F);
        }

        //submit selection for status screen

        for(int j = 0; j < 3; j++) {
            for(int k = 0; k < 2; k++) {

                int id = j * 2 + k;

                if(leftPos + 6 + 40 * k <= mouseX && leftPos + 6 + 40 * k + 18 > mouseX && topPos + 8 + 21 * j < mouseY && topPos + 8 + 21 * j + 18 >= mouseY) {
                    CompoundTag control = new CompoundTag();
                    control.putByte("toggle", (byte) id);
                    this.send(control);
                    this.click(0.5F);
                    return true;
                }

                if(leftPos + 24 + 40 * k <= mouseX && leftPos + 24 + 40 * k + 18 > mouseX && topPos + 8 + 21 * j < mouseY && topPos + 8 + 21 * j + 18 >= mouseY) {

                    CompoundTag control = new CompoundTag();
                    control.putByte("id", (byte) id);

                    for(int s = 0; s < selection.length; s++) {
                        if(selection[s]) {
                            control.putBoolean("s" + s, true);
                        }
                    }

                    this.send(control);
                    this.click(0.75F);
                    return true;
                }
            }
        }

        return super.mouseClicked(mouseX, mouseY, button);
    }

    private int[] selectedOfType(RBMKColumnType type) {
        List<Integer> ints = new ArrayList<>();
        for(int j = 0; j < be.columns.length; j++) {
            if(be.columns[j] != null && be.columns[j].type == type && this.selection[j]) {
                ints.add(j);
            }
        }
        return ints.stream().mapToInt(Integer::intValue).toArray();
    }

    private void send(CompoundTag control) {
        PacketDistributor.sendToServer(new CompoundTagControl(control, be.getBlockPos()));
    }

    /** The original's gui.button.press with the given pitch. */
    private void click(float pitch) {
        this.minecraft.getSoundManager().play(SimpleSoundInstance.forUI(SoundEvents.UI_BUTTON_CLICK, pitch));
    }

    private void play(SoundEvent sound, float pitch) {
        this.minecraft.getSoundManager().play(SimpleSoundInstance.forUI(sound, pitch));
    }

    // The original draws no title and no inventory label.
    @Override
    protected void renderLabels(GuiGraphics guiGraphics, int mouseX, int mouseY) { }

    /** Original drawGuiContainerBackgroundLayer (:302-441). */
    @Override
    protected void renderBg(GuiGraphics guiGraphics, float partialTicks, int mouseX, int mouseY) {
        guiGraphics.blit(TEXTURE, leftPos, topPos, 0, 0, imageWidth, imageHeight);

        if(az5Lid) {
            guiGraphics.blit(TEXTURE, leftPos + 30, topPos + 138, 228, 172, 28, 28);
        }

        for(int j = 0; j < 3; j++) {
            for(int k = 0; k < 2; k++) {
                int id = j * 2 + k;
                guiGraphics.blit(TEXTURE, leftPos + 6 + 40 * k, topPos + 8 + 21 * j, be.screens[id].type.offset, 238, 18, 18);
            }
        }

        int bX = 86;
        int bY = 11;
        int size = 10;

        for(int i = 0; i < be.columns.length; i++) {

            RBMKColumn col = be.columns[i];

            if(col == null)
                continue;

            int x = bX + size * (i % 15);
            int y = bY + size * (i / 15);

            int tX = col.type.offset;
            int tY = 172;

            guiGraphics.blit(TEXTURE, leftPos + x, topPos + y, tX, tY, size, size);

            int h = Math.min((int)Math.ceil((col.data.getDouble("heat") - 20) * 10 / col.data.getDouble("maxHeat")), 10);
            this.bar(guiGraphics, leftPos + x, topPos + y + size - h, 0, 192 - h, 10, h);

            switch(col.type) {

                case CONTROL:
                    int color = col.data.getShort("color");
                    if(color > -1)
                        guiGraphics.blit(TEXTURE, leftPos + x, topPos + y, color * size, 202, 10, 10);

                    // Falls through to the rod bar, as the original.
                case CONTROL_AUTO:
                    int fr = 8 - (int)Math.ceil((col.data.getDouble("level") * 8));
                    this.bar(guiGraphics, leftPos + x + 4, topPos + y + 1, 24, 183, 2, fr);
                    break;

                case FUEL:
                case FUEL_SIM:
                    if(col.data.contains("c_heat")) {
                        int fh = (int)Math.ceil((col.data.getDouble("c_heat") - 20) * 8 / col.data.getDouble("c_maxHeat"));
                        if(fh > 8) fh = 8;
                        this.bar(guiGraphics, leftPos + x + 1, topPos + y + size - fh - 1, 11, 191 - fh, 2, fh);

                        int fe = (int)Math.ceil((col.data.getDouble("enrichment")) * 8);
                        if(fe > 8) fe = 8;
                        this.bar(guiGraphics, leftPos + x + 4, topPos + y + size - fe - 1, 14, 191 - fe, 2, fe);

                        int fx = (int)Math.ceil((col.data.getDouble("xenon")) * 8 / 100);
                        if(fx > 8) fx = 8;
                        this.bar(guiGraphics, leftPos + x + 7, topPos + y + size - fx - 1, 17, 191 - fx, 2, fx);
                    }
                    break;

                case BOILER:
                    int fw = (int)Math.ceil((col.data.getInt("water")) * 8 / col.data.getDouble("maxWater"));
                    this.bar(guiGraphics, leftPos + x + 1, topPos + y + size - fw - 1, 41, 191 - fw, 3, fw);
                    int fs = (int)Math.ceil((col.data.getInt("steam")) * 8 / col.data.getDouble("maxSteam"));
                    this.bar(guiGraphics, leftPos + x + 6, topPos + y + size - fs - 1, 46, 191 - fs, 3, fs);

                    // The steam grade by fluid ID (the original compares with Fluids.X.ordinal(), its fluid ID).
                    short type = col.data.getShort("type");
                    if(type == Fluids.STEAM.getID())
                        guiGraphics.blit(TEXTURE, leftPos + x + 4, topPos + y + 1, 44, 183, 2, 2);
                    if(type == Fluids.HOTSTEAM.getID())
                        guiGraphics.blit(TEXTURE, leftPos + x + 4, topPos + y + 3, 44, 185, 2, 2);
                    if(type == Fluids.SUPERHOTSTEAM.getID())
                        guiGraphics.blit(TEXTURE, leftPos + x + 4, topPos + y + 5, 44, 187, 2, 2);
                    if(type == Fluids.ULTRAHOTSTEAM.getID())
                        guiGraphics.blit(TEXTURE, leftPos + x + 4, topPos + y + 7, 44, 189, 2, 2);

                    break;

                case HEATEX:
                    int cc = (int)Math.ceil((col.data.getInt("water")) * 8 / col.data.getDouble("maxWater"));
                    this.bar(guiGraphics, leftPos + x + 1, topPos + y + size - cc - 1, 131, 191 - cc, 3, cc);
                    int hc = (int)Math.ceil((col.data.getInt("steam")) * 8 / col.data.getDouble("maxSteam"));
                    this.bar(guiGraphics, leftPos + x + 6, topPos + y + size - hc - 1, 136, 191 - hc, 3, hc);
                    break;

                default:
                    break;
            }

            if(this.selection[i])
                guiGraphics.blit(TEXTURE, leftPos + x, topPos + y, 0, 192, 10, 10);
        }

        int highest = Integer.MIN_VALUE;
        int lowest = Integer.MAX_VALUE;

        for(int i : be.fluxBuffer) {
            if(i > highest) highest = i;
            if(i < lowest) lowest = i;
        }

        // The original draws GL_LINES 2 px wide; NEO draws each segment as a 2 px quad across the line.
        VertexConsumer consumer = guiGraphics.bufferSource().getBuffer(RenderType.gui());
        Matrix4f matrix = guiGraphics.pose().last().pose();
        int range = highest - lowest;
        for(int i = 0; i < be.fluxBuffer.length - 1; i++) {
            float[] px = new float[2];
            float[] py = new float[2];
            for(int j = 0; j < 2; j++) {
                int k = i + j;
                int flux = be.fluxBuffer[k];
                px[j] = (float) (leftPos + 7 + k * 74D / be.fluxBuffer.length);
                py[j] = (float) (topPos + 127 - (flux - lowest) * 24D / Math.max(range, 1));
            }
            this.segment(consumer, matrix, px[0], py[0], px[1], py[1]);
        }
        guiGraphics.flush();

        guiGraphics.pose().pushPose();
        float scale = 0.5F;
        guiGraphics.pose().scale(scale, scale, 1);
        guiGraphics.drawString(this.font, highest + "", (int) ((leftPos + 8) / scale), (int) ((topPos + 98) / scale), 0x00ff00, false);
        guiGraphics.drawString(this.font, highest + "", (int) ((leftPos + 80 - this.font.width(highest + "") * scale) / scale), (int) ((topPos + 98) / scale), 0x00ff00, false);
        guiGraphics.drawString(this.font, lowest + "", (int) ((leftPos + 8) / scale), (int) ((topPos + 133 - this.font.lineHeight * scale) / scale), 0x00ff00, false);
        guiGraphics.drawString(this.font, lowest + "", (int) ((leftPos + 80 - this.font.width(lowest + "") * scale) / scale), (int) ((topPos + 133 - this.font.lineHeight * scale) / scale), 0x00ff00, false);
        guiGraphics.pose().popPose();

        this.field.render(guiGraphics, mouseX, mouseY, partialTicks);
    }

    // A bar of the given height; a non-positive height draws nothing.
    private void bar(GuiGraphics guiGraphics, int x, int y, int u, int v, int width, int height) {
        if(height > 0) guiGraphics.blit(TEXTURE, x, y, u, v, width, height);
    }

    // One green flux graph segment, 2 px wide, in the vertex order GuiGraphics.fill uses so it survives back-face culling.
    private void segment(VertexConsumer consumer, Matrix4f matrix, float x1, float y1, float x2, float y2) {
        float dx = x2 - x1;
        float dy = y2 - y1;
        float length = Mth.sqrt(dx * dx + dy * dy);
        if(length <= 0F) return;

        float nx = -dy / length;
        float ny = dx / length;
        int color = 0xFF00FF00;

        consumer.addVertex(matrix, x1 - nx, y1 - ny, 0F).setColor(color);
        consumer.addVertex(matrix, x1 + nx, y1 + ny, 0F).setColor(color);
        consumer.addVertex(matrix, x2 + nx, y2 + ny, 0F).setColor(color);
        consumer.addVertex(matrix, x2 - nx, y2 - ny, 0F).setColor(color);
    }

    // Original keyTyped (:443-455). A focused field keeps every key, so typing never closes the screen on the inventory key; escape still does.
    @Override
    public boolean keyPressed(int keyCode, int scanCode, int modifiers) {
        if(keyCode == GLFW.GLFW_KEY_ESCAPE) return super.keyPressed(keyCode, scanCode, modifiers);

        if(this.field.keyPressed(keyCode, scanCode, modifiers)) return true;
        if(this.field.canConsumeInput()) return true;

        return super.keyPressed(keyCode, scanCode, modifiers);
    }

    @Override
    public boolean charTyped(char codePoint, int modifiers) {
        if(this.field.charTyped(codePoint, modifiers)) return true;

        return super.charTyped(codePoint, modifiers);
    }

    // Original doesGuiPauseGame.
    @Override
    public boolean isPauseScreen() {
        return false;
    }
}
