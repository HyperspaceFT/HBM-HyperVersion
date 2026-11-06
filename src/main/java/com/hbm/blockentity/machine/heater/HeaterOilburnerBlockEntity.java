package com.hbm.blockentity.machine.heater;

import api.hbm.fluidmk2.IFluidStandardTransceiverMK2;
import com.hbm.blockentity.IFluidCopiable;
import com.hbm.blockentity.IUpgradeInfoProvider;
import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.blocks.NtmBlocks;
import com.hbm.handler.pollution.PollutionHandler;
import com.hbm.handler.pollution.PollutionHandler.PollutionType;
import com.hbm.interfaces.IControlReceiver;
import com.hbm.inventory.FluidContainerRegistry;
import com.hbm.inventory.UpgradeManagerNT;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.fluid.tank.FluidTank;
import com.hbm.inventory.fluid.trait.FT_Flammable;
import com.hbm.inventory.fluid.trait.FT_Polluting;
import com.hbm.inventory.menus.HeaterOilburnerMenu;
import com.hbm.items.machine.IItemFluidIdentifier;
import com.hbm.items.machine.InfiniteFluidItem;
import com.hbm.items.machine.MachineUpgradeItem;
import com.hbm.items.machine.MachineUpgradeItem.UpgradeType;
import com.hbm.util.BobMathUtil;
import com.hbm.util.fauxpointtwelve.DirPos;
import net.minecraft.ChatFormatting;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.chat.Component;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.AbstractContainerMenu;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.level.block.state.BlockState;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class HeaterOilburnerBlockEntity extends AbstractHeaterMachineBlockEntity implements IFluidStandardTransceiverMK2, IControlReceiver, IFluidCopiable, IUpgradeInfoProvider {

    public static final int SLOT_UPGRADE = 3;
    // Original getValidUpgrades: overdrive up to level 3, so the burn rate never exceeds 10 * (3 + 1)
    private static final int MAX_OVERDRIVE = 3;
    private static final int HIGHEST_BURN_RATE = 10 * (MAX_OVERDRIVE + 1);

    public final FluidTank tank = new FluidTank(Fluids.HEATINGOIL, 16_000);
    public boolean isOn = false;
    /** Burn rate in mB/t (the original's burnRate), set with the GUI slider, 1..maxBurnRate. */
    public int setting = 1;
    /** Recomputed on the server every tick from the overdrive level and synced to the client. */
    public int maxBurnRate = 10;
    public int maxHeatEnergy = 500_000;

    public final UpgradeManagerNT upgradeManager = new UpgradeManagerNT(this);

    public HeaterOilburnerBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.HEATER_OILBURNER.get(), pos, state, 4);
    }

    @Override
    protected Component getDefaultName() {
        return Component.translatable("container.heaterOilburner");
    }

    @Override
    protected int getMaxHeat() {
        return this.maxHeatEnergy;
    }

    public DirPos[] getConPos() {
        return new DirPos[] {
                new DirPos(this.getBlockPos().getX() + 2, this.getBlockPos().getY(), this.getBlockPos().getZ(), Direction.EAST),
                new DirPos(this.getBlockPos().getX() - 2, this.getBlockPos().getY(), this.getBlockPos().getZ(), Direction.WEST),
                new DirPos(this.getBlockPos().getX(), this.getBlockPos().getY(), this.getBlockPos().getZ() + 2, Direction.SOUTH),
                new DirPos(this.getBlockPos().getX(), this.getBlockPos().getY(), this.getBlockPos().getZ() - 2, Direction.NORTH)
        };
    }

    @Override
    public void updateEntity() {
        if(this.level == null || this.level.isClientSide) return;

        int prevFill = this.tank.getFill();
        int prevHeat = this.heatEnergy;
        int prevSetting = this.setting;
        FluidType prevType = this.tank.getTankType();

        this.tank.loadTank(this.level, 0, 1, this.slots);
        this.tank.setType(2, this.slots);

        this.upgradeManager.checkSlots(this.slots, SLOT_UPGRADE, SLOT_UPGRADE);
        int overdrive = this.upgradeManager.getLevel(UpgradeType.OVERDRIVE);

        this.maxBurnRate = 10 * (overdrive + 1);
        this.maxHeatEnergy = 500_000 * (overdrive + 1);

        // Removing an overdrive upgrade lowers both limits at once
        this.setting = Math.min(this.setting, this.maxBurnRate);
        this.heatEnergy = Math.min(this.heatEnergy, this.maxHeatEnergy);

        for(DirPos pos : this.getConPos()) {
            this.trySubscribe(this.tank.getTankType(), this.level, pos);
        }

        boolean shouldCool = true;

        if(this.isOn && this.heatEnergy < this.maxHeatEnergy) {
            if(this.tank.getTankType().hasTrait(FT_Flammable.class)) {
                FT_Flammable trait = this.tank.getTankType().getTrait(FT_Flammable.class);
                int toBurn = Math.min(this.setting, this.tank.getFill());
                if(toBurn > 0) {
                    this.tank.setFill(this.tank.getFill() - toBurn);
                    this.heatEnergy += (int) (trait.getHeatEnergy() / 1000L) * toBurn;

                    if(this.level.getGameTime() % 5 == 0) {
                        this.pollute(this.tank.getTankType(), toBurn * 5);
                    }
                }

                // As in the original, a burner that is on with a flammable type keeps its heat even while the tank is empty
                shouldCool = false;
            }
        }

        if(this.heatEnergy >= this.maxHeatEnergy) {
            shouldCool = false;
        }

        if(shouldCool) {
            this.heatEnergy = Math.max(this.heatEnergy - Math.max(this.heatEnergy / 1000, 1), 0);
        }

        if(this.tank.getFill() != prevFill || this.heatEnergy != prevHeat || this.setting != prevSetting || this.tank.getTankType() != prevType) {
            this.setChanged();
        }

        this.networkPackNT(25);
    }

    /**
     * The original (TileEntityMachinePolluting) is called with amount = toBurn * 5: per call and burn pollution type it
     * puts ceil(value * amount * 100) mB into a 100 mB smoke tank, and once that tank is full, with no outlet attached,
     * each call overflows exactly the mB it added, releasing overflow / 100 into the world. NEO has no smoke tank or
     * outlet, so this emits that steady-state overflow directly; it skips the original's transient, in which the first
     * calls only fill the empty tank and release nothing until it reaches 100 mB.
     */
    private void pollute(FluidType type, float amount) {
        FT_Polluting trait = type.getTrait(FT_Polluting.class);
        if(trait == null) return;

        for(Map.Entry<PollutionType, Float> entry : trait.burnMap.entrySet()) {
            PollutionHandler.incrementPollution(this.level, this.worldPosition, entry.getKey(), (float) Math.ceil(entry.getValue() * amount * 100F) / 100F);
        }
    }

    @Override
    public boolean canProvideInfo(UpgradeType type, int lvl, TooltipFlag flag) {
        return type == UpgradeType.OVERDRIVE;
    }

    @Override
    public void provideInfo(UpgradeType type, int lvl, List<Component> components, TooltipFlag flag) {
        components.add(IUpgradeInfoProvider.getStandardLabel(NtmBlocks.HEATER_OILBURNER.get()));
        if(type == UpgradeType.OVERDRIVE) {
            components.add(Component.translatable(KEY_YES).withStyle(BobMathUtil.getBlink() ? ChatFormatting.RED : ChatFormatting.DARK_GRAY));
        }
    }

    @Override
    public HashMap<UpgradeType, Integer> getValidUpgrades() {
        HashMap<UpgradeType, Integer> upgrades = new HashMap<>(1);
        upgrades.put(UpgradeType.OVERDRIVE, MAX_OVERDRIVE);
        return upgrades;
    }

    @Override
    public AbstractContainerMenu createMenu(int id, Inventory inventory, Player player) {
        return new HeaterOilburnerMenu(id, inventory, this);
    }

    @Override
    public boolean canPlaceItem(int slot, ItemStack stack) {
        if(slot == 2) {
            return stack.getItem() instanceof IItemFluidIdentifier;
        }

        if(slot == SLOT_UPGRADE) {
            return stack.getItem() instanceof MachineUpgradeItem item && this.getValidUpgrades().containsKey(item.type);
        }

        if(slot == 0) {
            // Gas shale is a full container without an empty one (original ContainerOilburner.java:22 takes any item)
            return !FluidContainerRegistry.getEmptyContainer(stack).isEmpty()
                    || FluidContainerRegistry.getFluidContent(stack, this.tank.getTankType()) > 0
                    || stack.getItem() instanceof InfiniteFluidItem;
        }

        return false;
    }

    // Slots 0-2 keep the heater base's automation access; the overdrive upgrade stays out of it, as the original exposes no slot to automation
    @Override
    public int[] getSlotsForFace(Direction direction) {
        return new int[] {0, 1, 2};
    }

    @Override
    public FluidTank[] getReceivingTanks() {
        return new FluidTank[] { this.tank };
    }

    @Override
    public FluidTank[] getSendingTanks() {
        return FluidTank.EMPTY_ARRAY;
    }

    @Override
    public FluidTank[] getAllTanks() {
        return new FluidTank[] { this.tank };
    }

    @Override
    public boolean canConnect(FluidType type, Direction dir) {
        return dir != null && dir.getAxis().isHorizontal();
    }

    @Override
    public long transferFluid(FluidType type, int pressure, long amount) {
        long remainder = IFluidStandardTransceiverMK2.super.transferFluid(type, pressure, amount);
        // Pipes fill the tank between ticks; a burner that is off would otherwise never save that fluid.
        if(remainder < amount) this.setChanged();
        return remainder;
    }

    @Override
    public boolean hasPermission(Player player) {
        return player.distanceToSqr(this.getBlockPos().getX() + 0.5, this.getBlockPos().getY() + 0.5, this.getBlockPos().getZ() + 0.5) <= 256.0D;
    }

    @Override
    public void receiveControl(CompoundTag tag) {
        if(tag.contains("toggle")) {
            this.isOn = !this.isOn;
        }
        // The original takes the slider value unchecked; the server clamps it to the current limit
        if(tag.contains("setting")) {
            this.setting = Math.clamp(tag.getInt("setting"), 1, this.maxBurnRate);
        }
        this.setChanged();
    }

    @Override
    public CompoundTag getSettings(net.minecraft.world.level.Level level, BlockPos pos) {
        CompoundTag tag = IFluidCopiable.super.getSettings(level, pos);
        tag.putInt("setting", this.setting);
        tag.putBoolean("isOn", this.isOn);
        return tag;
    }

    @Override
    public void pasteSettings(CompoundTag tag, int index, net.minecraft.world.level.Level level, Player player, BlockPos pos) {
        IFluidCopiable.super.pasteSettings(tag, index, level, player, pos);
        if(tag.contains("setting")) this.setting = Math.clamp(tag.getInt("setting"), 1, this.maxBurnRate);
        if(tag.contains("isOn")) this.isOn = tag.getBoolean("isOn");
        this.setChanged();
    }

    @Override
    public void serialize(RegistryFriendlyByteBuf buf) {
        super.serialize(buf);
        this.tank.serialize(buf);
        buf.writeBoolean(this.isOn);
        buf.writeInt(this.setting);
        buf.writeInt(this.maxHeatEnergy);
        buf.writeInt(this.maxBurnRate);
    }

    @Override
    public void deserialize(RegistryFriendlyByteBuf buf) {
        super.deserialize(buf);
        this.tank.deserialize(buf);
        this.isOn = buf.readBoolean();
        this.setting = buf.readInt();
        this.maxHeatEnergy = buf.readInt();
        this.maxBurnRate = buf.readInt();
    }

    @Override
    protected void loadAdditional(CompoundTag tag, net.minecraft.core.HolderLookup.Provider registries) {
        super.loadAdditional(tag, registries);
        this.tank.readFromNBT(tag, "tank");
        this.isOn = tag.getBoolean("isOn");
        // Earlier NEO versions allowed up to 100. The upgrade level is not known until the first tick reads slot 3, so this
        // only bounds the rate by the highest overdrive level; the first server tick clamps it to the current maxBurnRate.
        this.setting = Math.clamp(tag.getInt("setting"), 1, HIGHEST_BURN_RATE);
    }

    @Override
    protected void saveAdditional(CompoundTag tag, net.minecraft.core.HolderLookup.Provider registries) {
        super.saveAdditional(tag, registries);
        this.tank.writeToNBT(tag, "tank");
        tag.putBoolean("isOn", this.isOn);
        tag.putInt("setting", this.setting);
    }
}
