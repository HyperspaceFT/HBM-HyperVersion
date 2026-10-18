package com.hbm.blockentity.machine;

import api.hbm.energymk2.IEnergyReceiverMK2;
import api.hbm.fluidmk2.IFluidStandardTransceiverMK2;
import com.hbm.blockentity.IUpgradeInfoProvider;
import com.hbm.blockentity.MachineBaseBlockEntity;
import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.blocks.NtmBlocks;
import com.hbm.interfaces.IControlReceiver;
import com.hbm.inventory.UpgradeManagerNT;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.fluid.tank.FluidTank;
import com.hbm.inventory.menus.MachinePUREXMenu;
import com.hbm.inventory.recipes.PUREXRecipes;
import com.hbm.inventory.recipes.loader.GenericRecipe;
import com.hbm.items.NtmItems;
import com.hbm.items.machine.BlueprintsItem;
import com.hbm.items.machine.MachineUpgradeItem;
import com.hbm.items.machine.MachineUpgradeItem.UpgradeType;
import com.hbm.lib.Library;
import com.hbm.main.NuclearTechMod;
import com.hbm.module.machine.ModuleMachinePUREX;
import com.hbm.registry.NtmSoundEvents;
import com.hbm.sound.AudioWrapper;
import com.hbm.util.BobMathUtil;
import com.hbm.util.fauxpointtwelve.DirPos;
import net.minecraft.ChatFormatting;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.HolderLookup;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.chat.Component;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.AbstractContainerMenu;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.AABB;

import java.util.HashMap;
import java.util.List;

/**
 * Original TileEntityMachinePUREX.java. Slots: 0 battery, 1 blueprint, 2-3 upgrades, 4-6 inputs, 7-12 outputs. Unlike the chemical
 * plant there are no fluid container slots. The redstone-over-radio values (original :308-323) are not ported.
 */
public class MachinePUREXBlockEntity extends MachineBaseBlockEntity implements IEnergyReceiverMK2, IFluidStandardTransceiverMK2, IUpgradeInfoProvider, IControlReceiver {

    public final FluidTank[] inputTanks = new FluidTank[3];
    public final FluidTank[] outputTanks = new FluidTank[1];

    public long power;
    public long maxPower = 1_000_000;
    public boolean didProcess = false;
    public boolean frame = false;
    public int anim;
    public int prevAnim;
    private AudioWrapper audio;

    public final ModuleMachinePUREX purexModule;
    public final UpgradeManagerNT upgradeManager = new UpgradeManagerNT(this);

    private AABB renderBox;

    public MachinePUREXBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.MACHINE_PUREX.get(), pos, state, 13);

        for(int i = 0; i < 3; i++) {
            this.inputTanks[i] = new FluidTank(Fluids.NONE, 24_000);
        }
        this.outputTanks[0] = new FluidTank(Fluids.NONE, 24_000);

        this.purexModule = new ModuleMachinePUREX(0, this, this.slots)
                .itemInput(4)
                .itemOutput(7)
                .fluidInput(this.inputTanks[0], this.inputTanks[1], this.inputTanks[2])
                .fluidOutput(this.outputTanks[0]);
    }

    @Override
    protected Component getDefaultName() {
        return Component.translatable("container.machinePUREX");
    }

    @Override
    public void updateEntity() {
        if(this.level == null) return;

        if(this.maxPower <= 0) {
            this.maxPower = 1_000_000;
        }

        if(!this.level.isClientSide) {
            for(DirPos pos : this.getConPos()) {
                this.trySubscribe(this.level, pos);

                for(FluidTank tank : this.inputTanks) {
                    if(tank.getTankType() != Fluids.NONE) {
                        this.trySubscribe(tank.getTankType(), this.level, pos);
                    }
                }

                for(FluidTank tank : this.outputTanks) {
                    if(tank.getFill() > 0) {
                        this.tryProvide(tank, this.level, pos);
                    }
                }
            }

            GenericRecipe recipe = this.purexModule.getRecipe();
            if(recipe != null) {
                this.maxPower = recipe.power * 100;
            }

            this.maxPower = BobMathUtil.max(this.power, this.maxPower, 1_000_000);
            this.power = Library.chargeTEFromItems(this.slots, 0, this.power, this.maxPower);
            this.upgradeManager.checkSlots(this.slots, 2, 3);

            double speed = 1D;
            double pow = 1D;
            speed += Math.min(this.upgradeManager.getLevel(UpgradeType.SPEED), 3) / 3D;
            speed += Math.min(this.upgradeManager.getLevel(UpgradeType.OVERDRIVE), 3);
            pow -= Math.min(this.upgradeManager.getLevel(UpgradeType.POWER), 3) * 0.25D;
            pow += Math.min(this.upgradeManager.getLevel(UpgradeType.SPEED), 3);
            pow += Math.min(this.upgradeManager.getLevel(UpgradeType.OVERDRIVE), 3) * 10D / 3D;

            // Recipe setup may reset or retype tanks even when there is no power or no item input.
            FluidTank[] tanks = this.getAllTanks();
            FluidType[] previousTypes = new FluidType[tanks.length];
            int[] previousFills = new int[tanks.length];
            int[] previousPressures = new int[tanks.length];
            for(int i = 0; i < tanks.length; i++) {
                previousTypes[i] = tanks[i].getTankType();
                previousFills[i] = tanks[i].getFill();
                previousPressures[i] = tanks[i].getPressure();
            }

            this.purexModule.update(speed, pow, true, this.slots.get(1));
            for(int i = 0; i < tanks.length; i++) {
                if(previousTypes[i] != tanks[i].getTankType() || previousFills[i] != tanks[i].getFill() || previousPressures[i] != tanks[i].getPressure()) {
                    this.setChanged();
                    break;
                }
            }
            this.didProcess = this.purexModule.didProcess;
            if(this.purexModule.markDirty) {
                this.setChanged();
            }

            this.networkPackNT(100);
        } else {
            this.prevAnim = this.anim;

            if(this.level.getGameTime() % 20 == 0) {
                this.frame = !this.level.getBlockState(this.worldPosition.above(5)).isAir();
            }

            if(this.didProcess) {
                this.anim++;
            }

            // The local player comes through the common proxy type (ServerProxy.me() returns null), so no client-only class is loaded here.
            Player me = NuclearTechMod.proxy.me();
            BlockPos pos = this.worldPosition;
            if(this.didProcess && me != null && me.distanceToSqr(pos.getX(), pos.getY(), pos.getZ()) < 25 * 25) {
                if(this.audio == null) {
                    this.audio = this.createAudioLoop();
                    if(this.audio != null) this.audio.startSound();
                } else if(!this.audio.isPlaying()) {
                    this.audio = this.rebootAudio(this.audio);
                }

                if(this.audio != null) {
                    this.audio.keepAlive();
                    this.audio.updateVolume(this.getVolume(1F));
                    this.audio.updatePitch(0.75F);
                }
            } else {
                this.stopAudio();
            }
        }
    }

    @Override
    public AudioWrapper createAudioLoop() {
        return AudioWrapper.getLoopedSound(NtmSoundEvents.CHEMICAL_PLANT_OPERATE.get(), SoundSource.BLOCKS, this, 1F, 15F, 0.75F, 15);
    }

    private void stopAudio() {
        if(this.audio != null) {
            this.audio.stopSound();
            this.audio = null;
        }
    }

    @Override
    public void onChunkUnloaded() {
        super.onChunkUnloaded();
        this.stopAudio();
    }

    @Override
    public void setRemoved() {
        super.setRemoved();
        this.stopAudio();
    }

    /**
     * Original TilePortShapes.purex (:47-66): one block outward from each of the 16 ring proxies around the core on the bottom
     * layer, the four corners connecting along both of their outer faces (20 connections). The ring is symmetric, so the
     * positions do not depend on the facing.
     */
    public DirPos[] getConPos() {
        int x = this.worldPosition.getX();
        int y = this.worldPosition.getY();
        int z = this.worldPosition.getZ();
        return new DirPos[] {
                new DirPos(x + 3, y, z - 1, Library.POS_X),
                new DirPos(x + 3, y, z, Library.POS_X),
                new DirPos(x + 3, y, z + 1, Library.POS_X),
                new DirPos(x + 3, y, z + 2, Library.POS_X),
                new DirPos(x + 2, y, z + 3, Library.POS_Z),
                new DirPos(x + 1, y, z + 3, Library.POS_Z),
                new DirPos(x, y, z + 3, Library.POS_Z),
                new DirPos(x - 1, y, z + 3, Library.POS_Z),
                new DirPos(x - 2, y, z + 3, Library.POS_Z),
                new DirPos(x - 3, y, z + 2, Library.NEG_X),
                new DirPos(x - 3, y, z + 1, Library.NEG_X),
                new DirPos(x - 3, y, z, Library.NEG_X),
                new DirPos(x - 3, y, z - 1, Library.NEG_X),
                new DirPos(x - 3, y, z - 2, Library.NEG_X),
                new DirPos(x - 2, y, z - 3, Library.NEG_Z),
                new DirPos(x - 1, y, z - 3, Library.NEG_Z),
                new DirPos(x, y, z - 3, Library.NEG_Z),
                new DirPos(x + 1, y, z - 3, Library.NEG_Z),
                new DirPos(x + 2, y, z - 3, Library.NEG_Z),
                new DirPos(x + 3, y, z - 2, Library.POS_X)
        };
    }

    @Override
    public void serialize(RegistryFriendlyByteBuf buf) {
        super.serialize(buf);
        for(FluidTank tank : this.inputTanks) tank.serialize(buf);
        for(FluidTank tank : this.outputTanks) tank.serialize(buf);
        buf.writeLong(this.power);
        buf.writeLong(this.maxPower);
        buf.writeBoolean(this.didProcess);
        this.purexModule.serialize(buf);
    }

    @Override
    public void deserialize(RegistryFriendlyByteBuf buf) {
        super.deserialize(buf);
        for(FluidTank tank : this.inputTanks) tank.deserialize(buf);
        for(FluidTank tank : this.outputTanks) tank.deserialize(buf);
        this.power = buf.readLong();
        this.maxPower = buf.readLong();
        this.didProcess = buf.readBoolean();
        this.purexModule.deserialize(buf);
    }

    @Override
    protected void loadAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.loadAdditional(tag, registries);
        for(int i = 0; i < 3; i++) {
            this.inputTanks[i].readFromNBT(tag, "i" + i);
        }
        this.outputTanks[0].readFromNBT(tag, "o0");
        this.power = tag.getLong("power");
        this.maxPower = tag.getLong("maxPower");
        this.purexModule.readFromNBT(tag);
    }

    @Override
    protected void saveAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.saveAdditional(tag, registries);
        for(int i = 0; i < 3; i++) {
            this.inputTanks[i].writeToNBT(tag, "i" + i);
        }
        this.outputTanks[0].writeToNBT(tag, "o0");
        tag.putLong("power", this.power);
        tag.putLong("maxPower", this.maxPower);
        this.purexModule.writeToNBT(tag);
    }

    @Override
    public boolean canPlaceItem(int slot, ItemStack stack) {
        if(slot == 0) return true;
        if(slot == 1 && stack.getItem() == NtmItems.BLUEPRINTS.get()) return true;
        if(slot >= 2 && slot <= 3 && stack.getItem() instanceof MachineUpgradeItem) return true;
        return this.purexModule.isItemValid(slot, stack);
    }

    @Override
    public boolean canTakeItemThroughFace(int index, ItemStack stack, Direction direction) {
        // Original: inputs that no longer fit the selected recipe can be pulled out as well
        return (index >= 7 && index <= 12) || this.purexModule.isSlotClogged(index);
    }

    @Override
    public int[] getSlotsForFace(Direction direction) {
        return new int[] {4, 5, 6, 7, 8, 9, 10, 11, 12};
    }

    @Override public long getPower() { return this.power; }
    @Override public void setPower(long power) { this.power = power; }
    @Override public long getMaxPower() { return this.maxPower; }

    @Override public FluidTank[] getReceivingTanks() { return this.inputTanks; }
    @Override public FluidTank[] getSendingTanks() { return this.outputTanks; }
    @Override
    public FluidTank[] getAllTanks() {
        return new FluidTank[] { this.inputTanks[0], this.inputTanks[1], this.inputTanks[2], this.outputTanks[0] };
    }

    @Override
    public long transferFluid(FluidType type, int pressure, long amount) {
        long remainder = IFluidStandardTransceiverMK2.super.transferFluid(type, pressure, amount);
        if(remainder < amount) this.setChanged();
        return remainder;
    }

    @Override
    public void useUpFluid(FluidType type, int pressure, long amount) {
        long previous = this.getFluidAvailable(type, pressure);
        IFluidStandardTransceiverMK2.super.useUpFluid(type, pressure, amount);
        if(this.getFluidAvailable(type, pressure) != previous) this.setChanged();
    }

    @Override
    public AbstractContainerMenu createMenu(int id, Inventory inventory, Player player) {
        return new MachinePUREXMenu(id, inventory, this);
    }

    @Override public boolean hasPermission(Player player) { return this.stillValid(player); }

    @Override
    public void receiveControl(CompoundTag tag) {
        if(tag.contains("index") && tag.contains("selection")) {
            int index = tag.getInt("index");
            if(index == 0) {
                String selection = tag.getString("selection");
                // As the chemical plant: only a known recipe, and a pooled one only with its blueprint installed ("null" clears)
                if(!"null".equals(selection)) {
                    GenericRecipe recipe = PUREXRecipes.INSTANCE.recipeNameMap.get(selection);
                    if(recipe == null || (recipe.isPooled() && !recipe.isPartOfPool(BlueprintsItem.grabPool(this.slots.get(1))))) return;
                }
                this.purexModule.recipe = selection;
                this.setChanged();
            }
        }
    }

    @Override
    public boolean canProvideInfo(UpgradeType type, int lvl, TooltipFlag flag) {
        return type == UpgradeType.SPEED || type == UpgradeType.POWER || type == UpgradeType.OVERDRIVE;
    }

    @Override
    public void provideInfo(UpgradeType type, int lvl, List<Component> components, TooltipFlag flag) {
        components.add(IUpgradeInfoProvider.getStandardLabel(NtmBlocks.MACHINE_PUREX.get()));
        if(type == UpgradeType.SPEED) {
            components.add(Component.translatable(KEY_SPEED, "+" + (lvl * 100 / 3) + "%").withStyle(ChatFormatting.GREEN));
            // The original text says +50% per level (:289), but the formula adds 100% per level (:110); the text follows the formula.
            components.add(Component.translatable(KEY_CONSUMPTION, "+" + (lvl * 100) + "%").withStyle(ChatFormatting.RED));
        }
        if(type == UpgradeType.POWER) {
            components.add(Component.translatable(KEY_CONSUMPTION, "-" + (lvl * 25) + "%").withStyle(ChatFormatting.GREEN));
        }
        if(type == UpgradeType.OVERDRIVE) {
            components.add(Component.translatable(KEY_YES).withStyle(BobMathUtil.getBlink() ? ChatFormatting.RED : ChatFormatting.DARK_GRAY));
        }
    }

    @Override
    public HashMap<UpgradeType, Integer> getValidUpgrades() {
        HashMap<UpgradeType, Integer> upgrades = new HashMap<>();
        upgrades.put(UpgradeType.SPEED, 3);
        upgrades.put(UpgradeType.POWER, 3);
        upgrades.put(UpgradeType.OVERDRIVE, 3);
        return upgrades;
    }

    public AABB getRenderBoundingBox() {
        if(this.renderBox == null) {
            int x = this.worldPosition.getX();
            int y = this.worldPosition.getY();
            int z = this.worldPosition.getZ();
            this.renderBox = new AABB(x - 2, y, z - 2, x + 3, y + 5, z + 3);
        }
        return this.renderBox;
    }
}
