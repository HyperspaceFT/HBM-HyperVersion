package com.hbm.blockentity.machine.rbmk;

import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.blockentity.machine.rbmk.RBMKControlManualBlockEntity.RBMKColor;
import com.hbm.interfaces.IControlReceiver;
import com.hbm.interfaces.ICopiable;
import com.hbm.inventory.menus.RBMKControlAutoMenu;
import com.hbm.util.EnumUtil;
import net.minecraft.core.BlockPos;
import net.minecraft.core.HolderLookup;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.AbstractContainerMenu;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.Vec3;

/**
 * Original TileEntityRBMKControlAuto: rbmk_control_auto, whose target insertion follows the column heat between two heat bounds
 * along one of three curves.
 * <p>
 * The function is never null here (upstream-shared, NEO defence): the original reads a missing "function" key as null and then
 * throws in the next tick's switch; NEO reads a missing or out-of-range value as LINEAR and therefore always writes and sends it
 * (the original sends it only when non-null but always reads it).
 */
public class RBMKControlAutoBlockEntity extends RBMKControlBlockEntity implements IControlReceiver, ICopiable {

    public RBMKFunction function = RBMKFunction.LINEAR;
    public double levelLower;
    public double levelUpper;
    public double heatLower;
    public double heatUpper;

    public RBMKControlAutoBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.RBMK_CONTROL_AUTO.get(), pos, state);
    }

    @Override
    public String getContainerName() {
        return "container.rbmkControlAuto";
    }

    // Measured from the block corner, as the original (:34-37).
    @Override
    public boolean hasPermission(Player player) {
        BlockPos pos = this.getBlockPos();
        return new Vec3(pos.getX() - player.getX(), pos.getY() - player.getY(), pos.getZ() - player.getZ()).length() < 20;
    }

    /** Original updateEntity (:39-80): the target is set before the parent moves the rods. */
    @Override
    public void updateEntity() {
        Level world = this.getLevel();
        if(world == null) return;

        if(!world.isClientSide) {

            double fauxLevel = 0;

            double lowerBound = Math.min(this.heatLower, this.heatUpper);
            double upperBound = Math.max(this.heatLower, this.heatUpper);

            if(this.heat < lowerBound) {
                fauxLevel = this.levelLower;

            } else if(this.heat > upperBound) {
                fauxLevel = this.levelUpper;

            } else {

                switch(this.function) {
                case LINEAR:
                    // my brain hasn't been this challenged since my math finals in
                    // '19
                    fauxLevel = (this.heat - this.heatLower) * ((this.levelUpper - this.levelLower) / (this.heatUpper - this.heatLower)) + this.levelLower;
                    break;

                case QUAD_UP:
                    // so this is how we roll, huh?
                    fauxLevel = Math.pow((this.heat - this.heatLower) / (this.heatUpper - this.heatLower), 2) * (this.levelUpper - this.levelLower) + this.levelLower;
                    break;
                case QUAD_DOWN:
                    // sometimes my genius is almost frightening
                    fauxLevel = Math.pow((this.heat - this.heatUpper) / (this.heatLower - this.heatUpper), 2) * (this.levelLower - this.levelUpper) + this.levelUpper;
                    break;
                }
            }

            this.targetLevel = fauxLevel * 0.01D;
            this.targetLevel = Mth.clamp(this.targetLevel, 0D, 1D);
        }

        super.updateEntity();
    }

    @Override
    protected void loadAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.loadAdditional(tag, registries);

        this.levelLower = tag.getDouble("levelLower");
        this.levelUpper = tag.getDouble("levelUpper");
        this.heatLower = tag.getDouble("heatLower");
        this.heatUpper = tag.getDouble("heatUpper");

        this.function = functionOf(tag.contains("function") ? tag.getInt("function") : 0);
    }

    @Override
    protected void saveAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.saveAdditional(tag, registries);

        tag.putDouble("levelLower", levelLower);
        tag.putDouble("levelUpper", levelUpper);
        tag.putDouble("heatLower", heatLower);
        tag.putDouble("heatUpper", heatUpper);
        tag.putInt("function", function.ordinal());
    }

    @Override
    public void serialize(RegistryFriendlyByteBuf buf) {
        super.serialize(buf);
        buf.writeDouble(this.levelLower);
        buf.writeDouble(this.levelUpper);
        buf.writeDouble(this.heatLower);
        buf.writeDouble(this.heatUpper);
        buf.writeInt(function.ordinal());
    }

    @Override
    public void deserialize(RegistryFriendlyByteBuf buf) {
        super.deserialize(buf);
        this.levelLower = buf.readDouble();
        this.levelUpper = buf.readDouble();
        this.heatLower = buf.readDouble();
        this.heatUpper = buf.readDouble();
        this.function = functionOf(buf.readInt());
    }

    private static RBMKFunction functionOf(int index) {
        return index >= 0 && index < RBMKFunction.values().length ? RBMKFunction.values()[index] : RBMKFunction.LINEAR;
    }

    /** Original receiveControl (:130-146); server side. */
    @Override
    public void receiveControl(CompoundTag data) {

        if(data.contains("function")) {
            // The original's modulus is the colour count (5): 3 and 4 index past the three functions and crash the server. NEO-only:
            // such a value is ignored.
            int c = Math.abs(data.getInt("function") % RBMKColor.values().length);
            if(c < RBMKFunction.values().length) this.function = RBMKFunction.values()[c];

        } else {

            double levelLower = data.getDouble("levelLower");
            double levelUpper = data.getDouble("levelUpper");
            double heatLower = data.getDouble("heatLower");
            double heatUpper = data.getDouble("heatUpper");

            // NEO-only: the original trusts the client; values outside what the GUI clamps to (GUIRBMKControlAuto :205-216, 0-100
            // for the levels, 0-9999 for the heats) reject the whole packet.
            if(inRange(levelLower, 100D) && inRange(levelUpper, 100D) && inRange(heatLower, 9999D) && inRange(heatUpper, 9999D)) {
                this.levelLower = levelLower;
                this.levelUpper = levelUpper;
                this.heatLower = heatLower;
                this.heatUpper = heatUpper;
            }
        }

        this.setChanged();
    }

    private static boolean inRange(double value, double max) {
        return Double.isFinite(value) && value >= 0D && value <= max;
    }

    public enum RBMKFunction {
        LINEAR,
        QUAD_UP,
        QUAD_DOWN
    }

    @Override
    public RBMKColumnType getConsoleType() {
        return RBMKColumnType.CONTROL_AUTO;
    }

    @Override
    public void getDiagData(CompoundTag nbt) {
        super.getDiagData(nbt);

        nbt.putDouble("levelLower", levelLower);
        nbt.putDouble("levelUpper", levelUpper);
        nbt.putDouble("heatLower", heatLower);
        nbt.putDouble("heatUpper", heatUpper);
        nbt.putInt("function", function.ordinal());
    }

    @Override
    public AbstractContainerMenu createMenu(int containerId, Inventory inventory, Player player) {
        return new RBMKControlAutoMenu(containerId, inventory, this);
    }

    @Override
    public CompoundTag getSettings(Level world, BlockPos pos) {
        CompoundTag data = new CompoundTag();
        data.putDouble("levelLower", levelLower);
        data.putDouble("levelUpper", levelUpper);
        data.putDouble("heatLower", heatLower);
        data.putDouble("heatUpper", heatUpper);
        data.putInt("function", function.ordinal());
        return data;
    }

    // NEO: setChanged so the pasted settings are saved; the original does not mark the tile here.
    @Override
    public void pasteSettings(CompoundTag nbt, int index, Level world, Player player, BlockPos pos) {
        if(nbt.contains("levelLower")) levelLower = nbt.getDouble("levelLower");
        if(nbt.contains("levelUpper")) levelUpper = nbt.getDouble("levelUpper");
        if(nbt.contains("heatLower")) heatLower = nbt.getDouble("heatLower");
        if(nbt.contains("heatUpper")) heatUpper = nbt.getDouble("heatUpper");
        if(nbt.contains("function")) function = EnumUtil.grabEnumSafely(RBMKFunction.class, nbt.getInt("function"));
        this.setChanged();
    }
}
