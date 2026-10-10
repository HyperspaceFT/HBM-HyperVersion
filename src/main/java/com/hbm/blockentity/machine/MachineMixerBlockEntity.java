package com.hbm.blockentity.machine;

import api.hbm.energymk2.IBatteryItem;
import api.hbm.energymk2.IEnergyReceiverMK2;
import api.hbm.energymk2.PowerNetMK2;
import api.hbm.fluidmk2.FluidNetMK2;
import api.hbm.fluidmk2.IFluidStandardTransceiverMK2;
import com.hbm.blockentity.IFluidCopiable;
import com.hbm.blockentity.IUpgradeInfoProvider;
import com.hbm.blockentity.MachineBaseBlockEntity;
import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.blocks.NtmBlocks;
import com.hbm.interfaces.IControlReceiver;
import com.hbm.inventory.FluidStack;
import com.hbm.inventory.UpgradeManagerNT;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.fluid.tank.FluidTank;
import com.hbm.inventory.menus.MachineMixerMenu;
import com.hbm.inventory.recipes.MixerRecipes;
import com.hbm.inventory.recipes.MixerRecipes.MixerRecipe;
import com.hbm.items.machine.IItemFluidIdentifier;
import com.hbm.items.machine.MachineUpgradeItem;
import com.hbm.items.machine.MachineUpgradeItem.UpgradeType;
import com.hbm.lib.Library;
import com.hbm.uninos.NodeNet;
import com.hbm.uninos.UniNodespace;
import com.hbm.util.fauxpointtwelve.DirPos;
import net.minecraft.ChatFormatting;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.HolderLookup;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.Tag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.chat.Component;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.AbstractContainerMenu;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.AABB;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;

public class MachineMixerBlockEntity extends MachineBaseBlockEntity implements IEnergyReceiverMK2, IFluidStandardTransceiverMK2, IUpgradeInfoProvider, IControlReceiver, IFluidCopiable {

    public static final long MAX_POWER = 10_000;
    public static final int INPUT_CAPACITY = 16_000;
    public static final int OUTPUT_CAPACITY = 24_000;
    public static final int SLOT_BATTERY = 0;
    public static final int SLOT_INPUT = 1;
    public static final int SLOT_IDENTIFIER = 2;
    public static final int SLOT_UPGRADE_FIRST = 3;
    public static final int SLOT_UPGRADE_LAST = 4;
    private static final int[] AUTOMATION_SLOTS = { SLOT_INPUT };

    public final FluidTank[] tanks = { new FluidTank(Fluids.NONE, INPUT_CAPACITY), new FluidTank(Fluids.NONE, INPUT_CAPACITY), new FluidTank(Fluids.NONE, OUTPUT_CAPACITY) };
    public final UpgradeManagerNT upgradeManager = new UpgradeManagerNT(this);
    public long power;
    public int progress;
    public int processTime;
    public int recipeIndex;
    public int consumption = 50;
    public boolean wasOn;
    public float rotation;
    public float prevRotation;
    private FluidType subscribedFirst;
    private FluidType subscribedSecond;

    public MachineMixerBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.MACHINE_MIXER.get(), pos, state, 5);
    }
    @Override protected Component getDefaultName() { return Component.translatable("container.machine_mixer"); }
    @Override public AbstractContainerMenu createMenu(int id, Inventory inventory, Player player) { return new MachineMixerMenu(id, inventory, this); }

    /** The four sides and bottom of the core, plus the upward face of the top proxy. */
    public DirPos[] getConPos() {
        BlockPos core = this.worldPosition;
        return new DirPos[] { new DirPos(core.west(), Direction.WEST), new DirPos(core.east(), Direction.EAST),
                new DirPos(core.north(), Direction.NORTH), new DirPos(core.south(), Direction.SOUTH),
                new DirPos(core.below(), Direction.DOWN), new DirPos(core.above(3), Direction.UP) };
    }

    @Override public void updateEntity() {
        if(this.level == null) return;
        if(this.level.isClientSide) {
            this.prevRotation = this.rotation;
            if(this.wasOn) this.rotation += 20F;
            if(this.rotation >= 360F) { this.rotation -= 360F; this.prevRotation -= 360F; }
            return;
        }
        long previousPower = this.power;
        int previousProgress = this.progress;
        int previousTime = this.processTime;
        int previousRecipe = this.recipeIndex;
        boolean previousOn = this.wasOn;
        FluidType[] previousTypes = new FluidType[3];
        int[] previousFills = new int[3];
        for(int i = 0; i < 3; i++) { previousTypes[i] = this.tanks[i].getTankType(); previousFills[i] = this.tanks[i].getFill(); }

        if(this.subscribedFirst != previousTypes[0] || this.subscribedSecond != previousTypes[1]) this.removeFluidSubscriptions();
        for(DirPos connection : this.getConPos()) {
            this.trySubscribe(this.level, connection);
            if(previousTypes[0] != Fluids.NONE) this.trySubscribe(previousTypes[0], this.level, connection);
            if(previousTypes[1] != Fluids.NONE && previousTypes[1] != previousTypes[0]) this.trySubscribe(previousTypes[1], this.level, connection);
            if(this.tanks[2].getFill() > 0) this.tryProvide(this.tanks[2], this.level, connection);
        }
        this.subscribedFirst = previousTypes[0];
        this.subscribedSecond = previousTypes[1];
        ItemStack previousBattery = this.slots.get(SLOT_BATTERY).copy();
        this.power = Library.chargeTEFromItems(this.slots, SLOT_BATTERY, this.power, MAX_POWER);
        boolean changed = !ItemStack.matches(previousBattery, this.slots.get(SLOT_BATTERY));
        if(this.tanks[2].setType(SLOT_IDENTIFIER, this.slots)) {
            this.removeFluidSubscriptions();
            changed = true;
        }
        this.recalculateUpgrades();
        this.wasOn = this.canProcess();
        if(this.wasOn) {
            // Malformed saved progress cannot wrap; a legitimate large-duration recipe still completes.
            this.progress = (int) Math.min(Integer.MAX_VALUE, (long) this.progress + 1);
            this.power -= this.consumption;
            if(this.progress >= this.processTime) { this.process(); this.progress = 0; }
        } else this.progress = 0;
        for(int i = 0; i < 3; i++) {
            if(this.tanks[i].getTankType() != previousTypes[i]) this.removeFluidSubscriptions();
            changed |= this.tanks[i].getTankType() != previousTypes[i] || this.tanks[i].getFill() != previousFills[i];
        }
        if(changed || this.power != previousPower || this.progress != previousProgress || this.processTime != previousTime
                || this.recipeIndex != previousRecipe || this.wasOn != previousOn) this.setChanged();
        this.networkPackNT(50);
    }

    public void recalculateUpgrades() {
        this.upgradeManager.checkSlots(this.slots, SLOT_UPGRADE_FIRST, SLOT_UPGRADE_LAST);
        int speed = this.upgradeManager.getLevel(UpgradeType.SPEED);
        int economy = this.upgradeManager.getLevel(UpgradeType.POWER);
        int overdrive = this.upgradeManager.getLevel(UpgradeType.OVERDRIVE);
        this.consumption = 50 + speed * 150;
        // The compound assignment truncates the whole subtraction, not the subtracted term.
        this.consumption -= this.consumption * economy * 0.25;
        this.consumption *= overdrive * 3 + 1;
    }
    public int getConsumption() { return this.consumption; }
    public MixerRecipe getRecipe() { return MixerRecipes.getOutput(this.tanks[2].getTankType(), this.recipeIndex); }

    private MixerRecipe setupRecipe() {
        MixerRecipe[] recipes = MixerRecipes.getOutput(this.tanks[2].getTankType());
        int normalized = recipes.length == 0 ? 0 : Math.floorMod(this.recipeIndex, recipes.length);
        if(this.recipeIndex != normalized) { this.recipeIndex = normalized; this.setChanged(); }
        if(recipes.length == 0) return null;
        MixerRecipe recipe = recipes[normalized];
        FluidStack first = recipe.input1();
        FluidStack second = recipe.input2();
        FluidType firstType = first == null ? Fluids.NONE : first.type;
        FluidType secondType = second == null ? Fluids.NONE : second.type;
        // Upstream configures/clears the input tanks even when there is insufficient energy.
        if(this.tanks[0].getTankType() != firstType || this.tanks[1].getTankType() != secondType) {
            this.removeFluidSubscriptions();
            this.tanks[0].setTankType(firstType);
            this.tanks[1].setTankType(secondType);
            this.setChanged();
        }
        return recipe;
    }
    private boolean hasMaterials(MixerRecipe recipe) {
        if(recipe == null) return false;
        FluidStack first = recipe.input1();
        FluidStack second = recipe.input2();
        if(first != null && this.tanks[0].getFill() < first.fill) return false;
        if(second != null && this.tanks[1].getFill() < second.fill) return false;
        if((long) this.tanks[2].getFill() + recipe.output() > this.tanks[2].getMaxFill()) return false;
        if(recipe.solidInput() != null) {
            ItemStack stack = this.slots.get(SLOT_INPUT);
            if(stack.isEmpty() || !recipe.solidInput().matchesRecipe(stack, true) || stack.getCount() < recipe.solidInput().stacksize) return false;
        }
        return true;
    }
    public boolean canProcess() {
        MixerRecipe recipe = this.setupRecipe();
        if(!this.hasMaterials(recipe) || this.power < this.consumption) return false;
        int speed = this.upgradeManager.getLevel(UpgradeType.SPEED);
        int overdrive = this.upgradeManager.getLevel(UpgradeType.OVERDRIVE);
        long time = recipe.processTime();
        time -= time * speed / 4;
        time /= overdrive + 1;
        this.processTime = (int) Math.max(1L, time);
        return true;
    }
    /** Complete the entire material transaction; this tick's energy has already been paid. */
    public boolean process() {
        MixerRecipe recipe = this.setupRecipe();
        if(!this.hasMaterials(recipe)) return false;
        FluidStack first = recipe.input1();
        FluidStack second = recipe.input2();
        if(first != null) this.tanks[0].setFill(this.tanks[0].getFill() - first.fill);
        if(second != null) this.tanks[1].setFill(this.tanks[1].getFill() - second.fill);
        if(recipe.solidInput() != null) this.removeItem(SLOT_INPUT, recipe.solidInput().stacksize);
        this.tanks[2].setFill(this.tanks[2].getFill() + recipe.output());
        this.setChanged();
        return true;
    }

    private void removeFluidSubscriptions() {
        if(this.level == null || this.level.isClientSide) return;
        for(NodeNet net : new ArrayList<>(UniNodespace.activeNodeNets)) if(net instanceof FluidNetMK2 fluidNet) {
            fluidNet.removeReceiver(this);
            fluidNet.removeProvider(this);
        }
        this.subscribedFirst = null;
        this.subscribedSecond = null;
    }
    private void removeNetworkSubscriptions() {
        if(this.level == null || this.level.isClientSide) return;
        this.removeFluidSubscriptions();
        for(NodeNet net : new ArrayList<>(UniNodespace.activeNodeNets)) if(net instanceof PowerNetMK2 powerNet) powerNet.removeReceiver(this);
    }
    @Override public void onChunkUnloaded() { this.removeNetworkSubscriptions(); super.onChunkUnloaded(); }
    @Override public void setRemoved() { this.removeNetworkSubscriptions(); super.setRemoved(); }
    @Override public long getPower() { return this.power; }
    @Override public long getMaxPower() { return MAX_POWER; }
    @Override public void setPower(long power) {
        long bounded = Math.max(0, Math.min(MAX_POWER, power));
        if(this.power != bounded) { this.power = bounded; this.setChanged(); }
    }
    @Override public FluidTank[] getAllTanks() { return this.tanks; }
    @Override public FluidTank[] getReceivingTanks() { return new FluidTank[] {this.tanks[0], this.tanks[1]}; }
    @Override public FluidTank[] getSendingTanks() { return new FluidTank[] {this.tanks[2]}; }
    @Override public long transferFluid(FluidType type, int pressure, long amount) {
        long remainder = IFluidStandardTransceiverMK2.super.transferFluid(type, pressure, amount);
        if(remainder < amount) this.setChanged();
        return remainder;
    }
    @Override public void useUpFluid(FluidType type, int pressure, long amount) {
        long previous = this.getFluidAvailable(type, pressure);
        IFluidStandardTransceiverMK2.super.useUpFluid(type, pressure, amount);
        if(this.getFluidAvailable(type, pressure) != previous) this.setChanged();
    }
    @Override public boolean canPlaceItem(int slot, ItemStack stack) {
        if(stack.isEmpty()) return false;
        return switch(slot) {
            case SLOT_BATTERY -> stack.getItem() instanceof IBatteryItem battery && battery.getDischargeRate(stack) > 0;
            case SLOT_INPUT -> {
                MixerRecipe recipe = this.getRecipe();
                yield recipe != null && recipe.solidInput() != null && recipe.solidInput().matchesRecipe(stack, true);
            }
            case SLOT_IDENTIFIER -> stack.getItem() instanceof IItemFluidIdentifier;
            case SLOT_UPGRADE_FIRST, SLOT_UPGRADE_LAST -> stack.getItem() instanceof MachineUpgradeItem upgrade
                    && upgrade.tier > 0 && this.getValidUpgrades().containsKey(upgrade.type);
            default -> false;
        };
    }
    @Override public int[] getSlotsForFace(Direction direction) { return AUTOMATION_SLOTS; }
    @Override public boolean canPlaceItemThroughFace(int slot, ItemStack stack, Direction direction) { return slot == SLOT_INPUT && this.canPlaceItem(slot, stack); }
    @Override public boolean canTakeItemThroughFace(int slot, ItemStack stack, Direction direction) { return false; }
    @Override public ItemStack removeItemNoUpdate(int slot) {
        ItemStack removed = super.removeItemNoUpdate(slot);
        if(!removed.isEmpty()) this.setChanged();
        return removed;
    }
    @Override public void clearContent() {
        boolean changed = !this.isEmpty();
        super.clearContent();
        if(changed) this.setChanged();
    }

    @Override public boolean hasPermission(Player player) {
        return this.level != null && !this.level.isClientSide && player.level() == this.level
                && player.containerMenu instanceof MachineMixerMenu menu && menu.be == this && this.stillValid(player);
    }
    @Override public void receiveControl(Player player, CompoundTag tag) {
        if(!this.hasPermission(player) || tag == null || tag.getAllKeys().size() != 1 || !tag.contains("toggle", Tag.TAG_BYTE) || !tag.getBoolean("toggle")) return;
        MixerRecipe[] recipes = MixerRecipes.getOutput(this.tanks[2].getTankType());
        if(recipes.length == 0) return;
        this.recipeIndex = (Math.floorMod(this.recipeIndex, recipes.length) + 1) % recipes.length;
        // A valid new variant retains progress; the next tick clears it only if processing is blocked.
        this.setChanged();
    }
    @Override public void receiveControl(CompoundTag tag) {
        // CompoundTagControl invokes both overloads; only the player-context overload performs work.
    }
    @Override public FluidTank getTankToPaste() { return this.tanks[2]; }
    @Override public void pasteSettings(CompoundTag tag, int index, Level level, Player player, BlockPos pos) {
        if(tag == null || level != this.level || level.isClientSide || !this.worldPosition.equals(pos)
                || player.level() != level || !this.stillValid(player) || !tag.contains("FluidID", Tag.TAG_INT_ARRAY)) return;
        int[] ids = tag.getIntArray("FluidID");
        if(index < 0 || index >= ids.length) return;
        FluidType type = Fluids.fromID(ids[index]);
        if(type == Fluids.NONE && ids[index] != Fluids.NONE.getID()) return;
        if(type != this.tanks[2].getTankType()) {
            this.removeFluidSubscriptions();
            this.tanks[2].setTankType(type);
            this.setChanged();
        }
    }
    @Override public HashMap<UpgradeType, Integer> getValidUpgrades() {
        HashMap<UpgradeType, Integer> upgrades = new HashMap<>();
        upgrades.put(UpgradeType.SPEED, 3);
        upgrades.put(UpgradeType.POWER, 3);
        upgrades.put(UpgradeType.OVERDRIVE, 6);
        return upgrades;
    }
    @Override public boolean canProvideInfo(UpgradeType type, int level, TooltipFlag flag) { return this.getValidUpgrades().containsKey(type); }
    @Override public void provideInfo(UpgradeType type, int level, List<Component> info, TooltipFlag flag) {
        info.add(IUpgradeInfoProvider.getStandardLabel(NtmBlocks.MACHINE_MIXER.get()));
        if(type == UpgradeType.SPEED) {
            info.add(Component.translatable(KEY_DELAY, "-" + level * 25 + "%").withStyle(ChatFormatting.GREEN));
            info.add(Component.translatable(KEY_CONSUMPTION, "+" + level * 300 + "%").withStyle(ChatFormatting.RED));
        }
        if(type == UpgradeType.POWER) info.add(Component.translatable(KEY_CONSUMPTION, "-" + level * 25 + "%").withStyle(ChatFormatting.GREEN));
        if(type == UpgradeType.OVERDRIVE) info.add(Component.translatable(KEY_YES).withStyle(ChatFormatting.RED));
    }
    @Override protected void loadAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.loadAdditional(tag, registries);
        this.power = Math.max(0, Math.min(MAX_POWER, tag.getLong("power")));
        this.progress = Math.max(0, tag.getInt("progress"));
        this.processTime = Math.max(0, tag.getInt("processTime"));
        this.recipeIndex = Math.max(0, tag.getInt("recipe"));
        CompoundTag tankData = tag.copy();
        for(int i = 0; i < 3; i++) {
            int capacity = i == 2 ? OUTPUT_CAPACITY : INPUT_CAPACITY;
            // The generic reader clamps against the saved maximum, including a missing/invalid zero maximum.
            // Supply this machine's fixed capacity before reading to preserve otherwise valid old fluid data.
            tankData.putInt(i + "_max", capacity);
            int pressure = tankData.getShort(i + "_p");
            if(pressure < 0 || pressure > HIGHEST_VALID_PRESSURE) tankData.putShort(i + "_p", (short) 0);
            this.tanks[i].readFromNBT(tankData, i + "");
            this.tanks[i].changeTankSize(capacity);
        }
        this.wasOn = false;
        this.subscribedFirst = null;
        this.subscribedSecond = null;
    }
    @Override protected void saveAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.saveAdditional(tag, registries);
        tag.putLong("power", this.power);
        tag.putInt("progress", this.progress);
        tag.putInt("processTime", this.processTime);
        tag.putInt("recipe", this.recipeIndex);
        for(int i = 0; i < 3; i++) this.tanks[i].writeToNBT(tag, i + "");
    }
    @Override public void serialize(RegistryFriendlyByteBuf buf) {
        super.serialize(buf);
        buf.writeLong(this.power);
        buf.writeInt(this.progress);
        buf.writeInt(this.processTime);
        buf.writeInt(this.recipeIndex);
        buf.writeInt(this.consumption);
        buf.writeBoolean(this.wasOn);
        for(FluidTank tank : this.tanks) tank.serialize(buf);
    }
    @Override public void deserialize(RegistryFriendlyByteBuf buf) {
        super.deserialize(buf);
        this.power = buf.readLong();
        this.progress = buf.readInt();
        this.processTime = buf.readInt();
        this.recipeIndex = buf.readInt();
        this.consumption = buf.readInt();
        this.wasOn = buf.readBoolean();
        for(FluidTank tank : this.tanks) tank.deserialize(buf);
    }
    public AABB getRenderBoundingBox() {
        return new AABB(this.worldPosition.getX(), this.worldPosition.getY(), this.worldPosition.getZ(),
                this.worldPosition.getX() + 1, this.worldPosition.getY() + 3, this.worldPosition.getZ() + 1);
    }
}
