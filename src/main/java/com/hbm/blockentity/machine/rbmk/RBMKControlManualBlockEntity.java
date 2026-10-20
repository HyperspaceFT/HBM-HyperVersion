package com.hbm.blockentity.machine.rbmk;

import api.hbm.redstoneoverradio.IRORInteractive;
import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.blocks.machine.rbmk.RBMKControlBlock;
import com.hbm.interfaces.IControlReceiver;
import com.hbm.interfaces.ICopiable;
import com.hbm.inventory.menus.RBMKControlMenu;
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
 * Original TileEntityRBMKControlManual: the manual control rods rbmk_control and the moderated rbmk_control_mod, moved from the GUI,
 * the console (Goal24E) or Redstone-over-Radio, with an optional colour group. The OpenComputers callbacks are not ported.
 */
public class RBMKControlManualBlockEntity extends RBMKControlBlockEntity implements IControlReceiver, ICopiable, IRORInteractive {

    public RBMKColor color;
    public double startingLevel;

    public RBMKControlManualBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.RBMK_CONTROL.get(), pos, state);
    }

    @Override
    public String getContainerName() {
        return "container.rbmkControl";
    }

    @Override
    public boolean isModerated() {
        return this.getBlockState().getBlock() instanceof RBMKControlBlock control && control.moderated;
    }

    @Override
    public void setTarget(double target) {
        this.targetLevel = target;
        this.startingLevel = this.level;
    }

    @Override
    public double getMult() {

        double surge = 0;

        if(this.targetLevel < this.startingLevel && Math.abs(this.level - this.targetLevel) > 0.01D) {
            surge = Math.sin(Math.pow((1D - this.level), 15) * Math.PI) * (this.startingLevel - this.targetLevel) * RBMKDials.getSurgeMod();

        }

        return this.level + surge;
    }

    // Measured from the block corner, as the original (:64-67).
    @Override
    public boolean hasPermission(Player player) {
        BlockPos pos = this.getBlockPos();
        return new Vec3(pos.getX() - player.getX(), pos.getY() - player.getY(), pos.getZ() - player.getZ()).length() < 20;
    }

    /** Original receiveControl (:69-89); server side. */
    @Override
    public void receiveControl(CompoundTag data) {

        if(data.contains("level")) {
            double target = data.getDouble("level");
            // NEO-only: the original trusts the client; a target outside the rod's travel (the GUI sends 0 to 1) is ignored.
            if(Double.isFinite(target) && target >= 0D && target <= 1D) {
                this.setTarget(target);
            }
        }

        if(data.contains("color")) {
            // The modulus comes first: the original's Math.abs(c) % 5 crashes for Integer.MIN_VALUE, the same index otherwise.
            int c = Math.abs(data.getInt("color") % RBMKColor.values().length); //to stop naughty kids from sending packets that crash the server

            RBMKColor newCol = RBMKColor.values()[c];

            if(newCol == this.color) {
                this.color = null;
            } else {
                this.color = newCol;
            }
        }

        this.setChanged();
    }

    @Override
    protected void loadAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.loadAdditional(tag, registries);

        if(tag.contains("startingLevel"))
            this.startingLevel = tag.getDouble("startingLevel");

        // NEO-only: an out-of-range saved colour reads as no group instead of throwing.
        if(tag.contains("color"))
            this.color = colorOf(tag.getInt("color"));
        else
            this.color = null;
    }

    @Override
    protected void saveAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.saveAdditional(tag, registries);

        tag.putDouble("startingLevel", this.startingLevel);
        tag.putDouble("mult", this.getMult());

        if(color != null)
            tag.putInt("color", color.ordinal());
    }

    @Override
    public void serialize(RegistryFriendlyByteBuf buf) {
        super.serialize(buf);
        buf.writeDouble(this.startingLevel);
        if(this.color != null)
            buf.writeInt(this.color.ordinal());
        else
            buf.writeInt(-1);
    }

    // The original clamps the index to [0, 5], which throws for 5; -1 and anything out of range read as no group here.
    @Override
    public void deserialize(RegistryFriendlyByteBuf buf) {
        super.deserialize(buf);
        this.startingLevel = buf.readDouble();
        this.color = colorOf(buf.readInt());
    }

    private static RBMKColor colorOf(int index) {
        return index >= 0 && index < RBMKColor.values().length ? RBMKColor.values()[index] : null;
    }

    public enum RBMKColor {
        RED,
        YELLOW,
        GREEN,
        BLUE,
        PURPLE
    }

    @Override
    public RBMKColumnType getConsoleType() {
        return RBMKColumnType.CONTROL;
    }

    @Override
    public CompoundTag getNBTForConsole() {
        CompoundTag data = super.getNBTForConsole();

        if(this.color != null)
            data.putShort("color", (short)this.color.ordinal());
        else
            data.putShort("color", (short)-1);

        return data;
    }

    @Override
    public void getDiagData(CompoundTag nbt) {
        super.getDiagData(nbt);

        nbt.putDouble("startingLevel", this.startingLevel);
        nbt.putDouble("mult", this.getMult());

        if(color != null)
            nbt.putInt("color", color.ordinal());
    }

    @Override
    public AbstractContainerMenu createMenu(int containerId, Inventory inventory, Player player) {
        return new RBMKControlMenu(containerId, inventory, this);
    }

    @Override
    public CompoundTag getSettings(Level world, BlockPos pos) {
        CompoundTag data = new CompoundTag();
        if(color != null) data.putInt("color", color.ordinal());
        return data;
    }

    @Override
    public void pasteSettings(CompoundTag nbt, int index, Level world, Player player, BlockPos pos) {
        if(nbt.contains("color")) {
            color = EnumUtil.grabEnumSafely(RBMKColor.class, nbt.getInt("color"));
        } else {
            color = null;
        }
        this.setChanged();
    }

    @Override
    public String[] getFunctionInfo() {
        return new String[] {
                PREFIX_VALUE + "extraction",
                PREFIX_FUNCTION + "setrods" + NAME_SEPARATOR + "percent",
                PREFIX_FUNCTION + "extendrods" + NAME_SEPARATOR + "percent"
        };
    }

    @Override
    public String runRORFunction(String name, String[] params) {

        if((PREFIX_FUNCTION + "setrods").equals(name) && params.length > 0) {
            int percent = IRORInteractive.parseInt(params[0], 0, 100);
            this.setTarget(percent / 100D);
            this.setChanged();
            return null;
        }

        if((PREFIX_FUNCTION + "extendrods").equals(name) && params.length > 0) {
            int percent = IRORInteractive.parseInt(params[0], -100, 100);
            this.setTarget(Mth.clamp(this.targetLevel + percent / 100D, 0D, 1D));
            this.setChanged();
            return null;
        }

        return null;
    }
}
