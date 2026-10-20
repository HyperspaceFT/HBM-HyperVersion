package com.hbm.blockentity.machine.rbmk;

import com.hbm.blockentity.MachineBaseBlockEntity;
import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.blockentity.machine.rbmk.RBMKControlManualBlockEntity.RBMKColor;
import com.hbm.interfaces.IControlReceiver;
import com.hbm.inventory.menus.RBMKConsoleMenu;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.HolderLookup;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.chat.Component;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.AbstractContainerMenu;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;

import java.util.ArrayList;
import java.util.List;

/**
 * Original TileEntityRBMKConsole: the console core. It watches the 15 x 15 columns around its linked target (set with the rbmk_tool),
 * keeps a flux history and six screens, and moves the manual control rods, their colour groups and the steam channel compressors on
 * request from the console screen. The OpenComputers callbacks (getColumnData, getRBMKPos, setLevel, setColumnLevel, setColorLevel,
 * setColor, pressAZ5; :564-829) are not ported (GOAL24 decisions 6 and 19).
 */
public class RBMKConsoleBlockEntity extends MachineBaseBlockEntity implements IControlReceiver {

    public int targetX;
    public int targetY;
    public int targetZ;

    public byte rotation;

    public static final int fluxDisplayBuffer = 60;
    public int[] fluxBuffer = new int[fluxDisplayBuffer];

    //made this one-dimensional because it's a lot easier to serialize
    public RBMKColumn[] columns = new RBMKColumn[15 * 15];

    public RBMKScreen[] screens = new RBMKScreen[6];

    public RBMKConsoleBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.RBMK_CONSOLE.get(), pos, state, 0);

        for(int i = 0; i < screens.length; i++) {
            screens[i] = new RBMKScreen();
        }
    }

    /** Original updateEntity (:70-85), server side; the full data rides only the packets serialized on a multiple of 10 ticks. */
    @Override
    public void updateEntity() {
        if(this.level == null || this.level.isClientSide) return;

        if(this.level.getGameTime() % 10 == 0) {
            rescan();
            prepareScreenInfo();
        }

        this.networkPackNT(50);
    }

    /** Original rescan (:87-122); public in NEO so the GameTests can drive it. */
    public void rescan() {

        double flux = 0;

        for(int index = 0; index < columns.length; index++) {

            BlockEntity te = this.getColumnEntity(index);

            if(te instanceof RBMKBaseBlockEntity rbmk) {

                columns[index] = new RBMKColumn(rbmk.getConsoleType(), rbmk.getNBTForConsole());
                columns[index].data.putDouble("heat", rbmk.heat);
                columns[index].data.putDouble("maxHeat", rbmk.maxHeat());
                // The original writes the column's craneIndicator, a field of the RBMK crane (Goal 25) that NEO's columns do not have yet.
                columns[index].data.putByte("indicator", (byte) 0);
                if(rbmk.isModerated()) columns[index].data.putBoolean("moderated", true); //false is the default anyway and not setting it when we don't need to reduces cruft

                if(te instanceof RBMKRodBlockEntity fuel) {
                    flux += fuel.lastFluxQuantity;
                }

            } else {
                columns[index] = null;
            }
        }

        for(int i = 0; i < this.fluxBuffer.length - 1; i++) {
            this.fluxBuffer[i] = this.fluxBuffer[i + 1];
        }

        this.fluxBuffer[this.fluxBuffer.length - 1] = (int) flux;
    }

    /**
     * The column block entity at the given console index, rotated around the target. Like the original's Compat.getTileStandard
     * this never loads a chunk: an unloaded position reads as no column.
     */
    private BlockEntity getColumnEntity(int index) {
        BlockPos pos = new BlockPos(targetX + getXFromIndex(index), targetY, targetZ + getZFromIndex(index));
        return this.level.isLoaded(pos) ? this.level.getBlockEntity(pos) : null;
    }

    /**
     * Original prepareScreenInfo (:124-188); public in NEO so the GameTests can drive it. A screen whose columns hold no matching
     * value divides 0 by 0, as the original: (int) NaN is 0, so it shows 0.0.
     */
    public void prepareScreenInfo() {

        for(RBMKScreen screen : this.screens) {

            if(screen.type == ScreenType.NONE) {
                screen.display = null;
                continue;
            }

            double value = 0;
            int count = 0;

            for(int i : screen.columns) {

                // NEO-only: an index outside the grid can only come from an edited save; the original would throw.
                if(i < 0 || i >= this.columns.length) continue;

                RBMKColumn col = this.columns[i];

                if(col == null) continue;

                switch(screen.type) {
                    case COL_TEMP:
                        count++;
                        value += col.data.getDouble("heat");
                        break;
                    case FUEL_DEPLETION:
                        if(col.data.contains("enrichment")) {
                            count++;
                            value += (100D - (col.data.getDouble("enrichment") * 100D));
                        }
                        break;
                    case FUEL_POISON:
                        if(col.data.contains("xenon")) {
                            count++;
                            value += col.data.getDouble("xenon");
                        }
                        break;
                    case FUEL_TEMP:
                        if(col.data.contains("c_heat")) {
                            count++;
                            value += col.data.getDouble("c_heat");
                        }
                        break;
                    case ROD_EXTRACTION:
                        if(col.data.contains("level")) {
                            count++;
                            value += col.data.getDouble("level") * 100;
                        }
                        break;
                    default:
                        break;
                }
            }

            double result = value / (double) count;
            String text = ((int)(result * 10)) / 10D + "";

            switch(screen.type) {
                case COL_TEMP: text = "rbmk.screen.temp=" + text + "°C"; break;
                case FUEL_DEPLETION: text = "rbmk.screen.depletion=" + text + "%"; break;
                case FUEL_POISON: text = "rbmk.screen.xenon=" + text + "%"; break;
                case FUEL_TEMP: text = "rbmk.screen.core=" + text + "°C"; break;
                case ROD_EXTRACTION: text = "rbmk.screen.rod=" + text + "%"; break;
                default: break;
            }

            screen.display = text;
        }
    }

    /**
     * Original serialize (:190-220): on a multiple of 10 ticks the columns, the flux history and the six display texts, otherwise the
     * six screen types only. A missing display text is a false presence flag instead of the original's length -1.
     */
    @Override
    public void serialize(RegistryFriendlyByteBuf buf) {
        super.serialize(buf);

        if(this.level != null && this.level.getGameTime() % 10 == 0) {
            buf.writeBoolean(true);

            for(RBMKColumn column : this.columns) {
                if(column == null || column.type == null) {
                    buf.writeByte(-1);
                } else {
                    buf.writeByte((byte) column.type.ordinal());
                    buf.writeNbt(column.data);
                }
            }

            buf.writeVarIntArray(this.fluxBuffer);

            for(RBMKScreen screen : this.screens) {
                buf.writeBoolean(screen.display != null);
                if(screen.display != null) buf.writeUtf(screen.display);
            }

        } else {

            buf.writeBoolean(false);

            for(RBMKScreen screen : this.screens) {
                buf.writeByte((byte) screen.type.ordinal());
            }
        }
    }

    /** Original deserialize (:222-249). NEO-only: an unknown column or screen type reads as no column / NONE, and the flux history is capped at its size. */
    @Override
    public void deserialize(RegistryFriendlyByteBuf buf) {
        super.deserialize(buf);

        if(buf.readBoolean()) { // check if it should be a full packet

            RBMKColumnType[] types = RBMKColumnType.values();

            for(int i = 0; i < this.columns.length; i++) {
                byte ordinal = buf.readByte();
                if(ordinal < 0) {
                    this.columns[i] = null;
                } else {
                    // The compound follows every non-negative ordinal; it is read even when the type is unknown to keep the stream aligned.
                    CompoundTag data = buf.readNbt();
                    this.columns[i] = ordinal < types.length ? new RBMKColumn(types[ordinal], data) : null;
                }
            }

            this.fluxBuffer = buf.readVarIntArray(fluxDisplayBuffer);

            for(RBMKScreen screen : this.screens) {
                screen.display = buf.readBoolean() ? buf.readUtf() : null;
            }

        } else {

            for(RBMKScreen screen : this.screens) {
                screen.type = screenTypeOf(buf.readByte());
            }
        }
    }

    private static ScreenType screenTypeOf(int ordinal) {
        return ordinal >= 0 && ordinal < ScreenType.values().length ? ScreenType.values()[ordinal] : ScreenType.NONE;
    }

    // Measured from the block corner, as the original (:251-254).
    @Override
    public boolean hasPermission(Player player) {
        BlockPos pos = this.getBlockPos();
        return new Vec3(pos.getX() - player.getX(), pos.getY() - player.getY(), pos.getZ() - player.getZ()).length() < 20;
    }

    /**
     * Original receiveControl (:256-337), server side: five independent groups. The original trusts the client; NEO validates
     * every value it uses to reach a block or an array (NEO-only, commented at each check). The console screen's AZ-5 is the
     * "level" group with level 0 (see {@link #buildAZ5Control}).
     */
    @Override
    public void receiveControl(CompoundTag data) {

        if(data.contains("level")) {

            double target = data.getDouble("level");

            // NEO-only: a non-finite level is ignored instead of being clamped.
            if(Double.isFinite(target)) {

                target = Mth.clamp(target, 0, 1);
                int processed = 0;

                for(String key : data.getAllKeys()) {

                    if(key.startsWith("sel_")) {

                        // NEO-only: no more selections than the grid has columns.
                        if(processed++ >= this.columns.length) break;

                        int index = data.getInt(key);

                        // NEO-only: an index outside the grid would reach an arbitrary block.
                        if(index < 0 || index >= this.columns.length) continue;

                        if(this.getColumnEntity(index) instanceof RBMKControlManualBlockEntity rod) {
                            rod.startingLevel = rod.level;
                            rod.setTarget(target);
                            rod.setChanged();
                        }
                    }
                }
            }
        }

        if(data.contains("toggle")) {
            int slot = data.getByte("toggle");

            // NEO-only: an unknown screen is ignored; the original throws.
            if(slot >= 0 && slot < this.screens.length) {
                int next = this.screens[slot].type.ordinal() + 1;
                ScreenType type = ScreenType.values()[next % ScreenType.values().length];
                this.screens[slot].type = type;
                // NEO-only: the screen types are saved, so mark the console for saving; the original does not.
                this.setChanged();
            }
        }

        if(data.contains("id")) {
            int slot = data.getByte("id");

            // NEO-only: an unknown screen is ignored; the original throws.
            if(slot >= 0 && slot < this.screens.length) {
                List<Integer> list = new ArrayList<>();

                for(int i = 0; i < 15 * 15; i++) {
                    if(data.getBoolean("s" + i)) {
                        list.add(i);
                    }
                }

                this.screens[slot].columns = list.stream().mapToInt(Integer::intValue).toArray();
                // NEO-only: as for "toggle", the assignment is saved.
                this.setChanged();
            }
        }

        if(data.contains("assignColor")) {
            int color = data.getByte("assignColor");
            // EnumUtil.grabEnumSafely in the original: abs(index % length).
            RBMKColor group = RBMKColor.values()[Math.abs(color % RBMKColor.values().length)];

            for(int i : selectedColumns(data)) {
                if(this.getColumnEntity(i) instanceof RBMKControlManualBlockEntity rod) {
                    rod.color = group;
                    rod.setChanged();
                }
            }
        }

        if(data.contains("compressor")) {
            for(int i : selectedColumns(data)) {
                if(this.getColumnEntity(i) instanceof RBMKBoilerBlockEntity boiler) {
                    boiler.cyceCompressor();
                }
            }
        }
    }

    /** The "cols" indices of a control packet. NEO-only: at most one per column of the grid, and indices outside the grid are dropped. */
    private int[] selectedColumns(CompoundTag data) {
        int[] cols = data.getIntArray("cols");
        int count = Math.min(cols.length, this.columns.length);
        List<Integer> valid = new ArrayList<>();

        for(int k = 0; k < count; k++) {
            if(cols[k] >= 0 && cols[k] < this.columns.length) valid.add(cols[k]);
        }

        return valid.stream().mapToInt(Integer::intValue).toArray();
    }

    /**
     * The control data the console screen's AZ-5 button sends (GUIRBMKConsole :229-235): level 0 for every manual control rod
     * column of the given grid. Automatic rods are not selected; the server only moves manual rods anyway.
     */
    public static CompoundTag buildAZ5Control(RBMKColumn[] columns) {
        CompoundTag control = new CompoundTag();
        control.putDouble("level", 0);

        for(int j = 0; j < columns.length; j++) {
            if(columns[j] != null && columns[j].type == RBMKColumnType.CONTROL)
                control.putInt("sel_" + j, j);
        }

        return control;
    }

    /** Original getRenderBoundingBox (:339-342). */
    public AABB getRenderBoundingBox() {
        BlockPos pos = this.getBlockPos();
        return new AABB(pos.getX() - 2, pos.getY(), pos.getZ() - 2, pos.getX() + 3, pos.getY() + 4, pos.getZ() + 3);
    }

    public void setTarget(int x, int y, int z) {
        this.targetX = x;
        this.targetY = y;
        this.targetZ = z;
        this.setChanged();
    }

    // Original NBT keys (:357-385); the columns and the flux history are not saved.
    @Override
    protected void loadAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.loadAdditional(tag, registries);

        this.targetX = tag.getInt("tX");
        this.targetY = tag.getInt("tY");
        this.targetZ = tag.getInt("tZ");

        for(int i = 0; i < this.screens.length; i++) {
            // NEO-only: an unknown saved type reads as NONE instead of throwing.
            this.screens[i].type = screenTypeOf(tag.getByte("t" + i));
            this.screens[i].columns = tag.getIntArray("s" + i);
        }
        // NEO-only: the rotation is kept within the four quarter turns.
        this.rotation = (byte) (tag.getByte("rotation") & 3);
    }

    @Override
    protected void saveAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.saveAdditional(tag, registries);

        tag.putInt("tX", this.targetX);
        tag.putInt("tY", this.targetY);
        tag.putInt("tZ", this.targetZ);

        for(int i = 0; i < this.screens.length; i++) {
            tag.putByte("t" + i, (byte) this.screens[i].type.ordinal());
            tag.putIntArray("s" + i, this.screens[i].columns);
        }
        tag.putByte("rotation", this.rotation);
    }

    /** Original rotate (:387-389), turned by the screwdriver (RBMKConsole.onScrew). NEO also marks the console for saving; the original only changes the field. */
    public void rotate() {
        rotation = (byte)((rotation + 1) % 4);
        this.setChanged();
    }

    public int getXFromIndex(int col) {
        final int i = col % 15 - 7;
        final int j = col / 15 - 7;
        switch (rotation) {
            case 0: // 0°
                return i;
            case 1: // 90°
                return -j;
            case 2: // 180°
                return -i;
            case 3: // 270°
                return j;
        }

        return i;
    }

    public int getZFromIndex(int col) {
        final int i = col % 15 - 7;
        final int j = col / 15 - 7;
        switch (rotation) {
            case 0: // 0°
                return j;
            case 1: // 90°
                return i;
            case 2: // 180°
                return -j;
            case 3: // 270°
                return -i;
        }

        return j;
    }

    // The original getName returns null (:65-68): the console has no title of its own, the menu shows the block name.
    @Override
    protected Component getDefaultName() {
        return Component.translatable(this.getBlockState().getBlock().getDescriptionId());
    }

    // No slots: nothing is exposed to hoppers or pipes (the parent's default face slot {0} would be out of range).
    @Override
    public int[] getSlotsForFace(Direction direction) {
        return new int[0];
    }

    @Override
    public AbstractContainerMenu createMenu(int containerId, Inventory inventory, Player player) {
        return new RBMKConsoleMenu(containerId, inventory, this);
    }

    /** Original RBMKColumn (:425-500); getFancyStats is client code and lives in RBMKConsoleScreen. */
    public static class RBMKColumn {

        public RBMKColumnType type;
        public CompoundTag data;

        public RBMKColumn(RBMKColumnType type, CompoundTag data) {
            this.type = type;

            if(data != null) {
                this.data = data;
            } else {
                this.data = new CompoundTag();
            }
        }
    }

    /** Original RBMKScreen (:525-536), with an int array for the column indices. */
    public static class RBMKScreen {
        public ScreenType type = ScreenType.NONE;
        public int[] columns = new int[0];
        public String display = null;
    }

    /** Original ScreenType (:538-551); the offset is the icon's u in the console GUI texture. */
    public enum ScreenType {
        NONE(0 * 18),
        COL_TEMP(1 * 18),
        ROD_EXTRACTION(2 * 18),
        FUEL_DEPLETION(3 * 18),
        FUEL_POISON(4 * 18),
        FUEL_TEMP(5 * 18);

        public final int offset;

        ScreenType(int offset) {
            this.offset = offset;
        }
    }
}
