package com.hbm.blockentity.machine;

import api.hbm.energymk2.IBatteryItem;
import api.hbm.energymk2.IEnergyReceiverMK2;
import com.hbm.blockentity.IUpgradeInfoProvider;
import com.hbm.blockentity.MachineBaseBlockEntity;
import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.NtmBlocks;
import com.hbm.inventory.UpgradeManagerNT;
import com.hbm.inventory.menus.MachineArcFurnaceMenu;
import com.hbm.inventory.recipes.ArcFurnaceRecipes;
import com.hbm.inventory.recipes.ArcFurnaceRecipes.ArcFurnaceRecipe;
import com.hbm.items.NtmItems;
import com.hbm.items.machine.ArcElectrodeItem;
import com.hbm.items.machine.MachineUpgradeItem;
import com.hbm.items.machine.MachineUpgradeItem.UpgradeType;
import com.hbm.lib.Library;
import com.hbm.main.NuclearTechMod;
import com.hbm.particle.NtmParticleTypes;
import com.hbm.particle.vanilla.NbtParticleOptions;
import com.hbm.registry.NtmSoundEvents;
import com.hbm.sound.AudioWrapper;
import com.hbm.util.SoundUtils;
import com.hbm.util.fauxpointtwelve.DirPos;
import com.hbm.util.particle.ParticleUtil;
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
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.level.block.state.BlockState;

import java.util.HashMap;
import java.util.List;

/**
 * Original TileEntityMachineArcFurnaceLarge, solid mode only (GOAL13B B1): no liquidMode, molten contents, pouring or
 * liquid sync. The SOOT pollution, the AE2 item hooks (distributeInput / collectRequested) and the control receiver for
 * the liquid toggle are not ported (B10).
 */
public class MachineArcFurnaceBlockEntity extends MachineBaseBlockEntity implements IEnergyReceiverMK2, IUpgradeInfoProvider {

    private static final int INV_SIZE = 30;
    public static final long MAX_POWER = 2_500_000L;

    public static final byte ELECTRODE_NONE = 0;
    public static final byte ELECTRODE_FRESH = 1;
    public static final byte ELECTRODE_USED = 2;
    public static final byte ELECTRODE_DEPLETED = 3;

    public final UpgradeManagerNT upgradeManager = new UpgradeManagerNT(this);
    public long power;
    public float progress;
    public boolean isProgressing;
    public boolean hasMaterial;
    public int delay;
    public int upgrade;

    public float lid;
    /** Client only: the lid of the previous tick, for the renderer's partial-tick interpolation. */
    public float prevLid;
    private float syncLid;
    private int approachNum;

    /** Electrodes 0-2 as ELECTRODE_NONE / FRESH / USED / DEPLETED, decided on the server and synced. */
    public final byte[] electrodeStates = new byte[3];

    private AudioWrapper audioLid;
    private AudioWrapper audioProgress;

    public MachineArcFurnaceBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.MACHINE_ARC_FURNACE.get(), pos, state, INV_SIZE);
    }

    @Override
    protected Component getDefaultName() {
        return Component.translatable("container.machine_arc_furnace");
    }

    public int getMaxInputSize() {
        return this.upgrade == 0 ? 1 : this.upgrade == 1 ? 4 : this.upgrade == 2 ? 8 : 16;
    }

    public int getUpgradeLevel() {
        return this.upgrade;
    }

    /** HE per tick while processing: 1,000 / 5,000 / 25,000 / 125,000 by speed upgrade. */
    public long getConsumption() {
        return (long) (1_000 * Math.pow(5, this.upgrade));
    }

    @Override
    public void setItem(int index, ItemStack stack) {
        super.setItem(index, stack);

        if(this.level != null && !this.level.isClientSide && index == 4 && stack.getItem() instanceof MachineUpgradeItem) {
            SoundUtils.playAtVec3(this.level, this.getBlockPos().getCenter(), NtmSoundEvents.UPGRADE_PLUG.get(), SoundSource.BLOCKS);
        }
    }

    @Override
    public void updateEntity() {
        if(this.level == null) return;

        // Both sides, as the original, so the client's menu slots size the input grid the same way.
        this.upgradeManager.checkSlots(this.slots, 4, 4);
        this.upgrade = this.upgradeManager.getLevel(UpgradeType.SPEED);

        if(!this.level.isClientSide) {

            for(DirPos pos : this.getConPos()) {
                this.trySubscribe(this.level, pos);
            }

            this.power = Library.chargeTEFromItems(this.slots, 3, this.power, MAX_POWER);
            this.isProgressing = false;

            if(this.lid > 0) this.loadIngredients();

            if(this.power > 0) {

                boolean ingredients = this.hasIngredients();
                boolean electrodes = this.hasElectrodes();

                long consumption = this.getConsumption();

                if(ingredients && electrodes && this.delay <= 0) {
                    if(this.lid > 0) {
                        this.lid -= 1F / (60F / (this.upgrade * 0.5 + 1));
                        if(this.lid < 0) this.lid = 0;
                        this.progress = 0;
                    } else {

                        if(this.power >= consumption) {
                            int duration = 400 / (this.upgrade * 2 + 1);
                            this.progress += 1F / duration;
                            this.isProgressing = true;
                            this.power -= consumption;
                            if(this.progress >= 1F) {
                                this.process();
                                this.progress = 0;
                                this.setChanged();
                                this.delay = (int) (120 / (this.upgrade * 0.5 + 1));
                            }
                        }
                    }
                } else {
                    if(this.delay > 0) this.delay--;
                    this.progress = 0;
                    if(this.lid < 1) {
                        this.lid += 1F / (60F / (this.upgrade * 0.5 + 1));
                        if(this.lid > 1) this.lid = 1;
                    }
                }

                this.hasMaterial = ingredients;
            }

            this.decideElectrodeState();

            if(!this.hasMaterial) this.hasMaterial = this.hasIngredients();

            this.networkPackNT(150);
        } else {

            this.prevLid = this.lid;

            if(this.approachNum > 0) {
                this.lid = this.lid + ((this.syncLid - this.lid) / (float) this.approachNum);
                --this.approachNum;
            } else {
                this.lid = this.syncLid;
            }

            if(this.lid != this.prevLid) {
                if(this.audioLid == null || !this.audioLid.isPlaying()) {
                    this.audioLid = AudioWrapper.getLoopedSound(NtmSoundEvents.WGH_START.get(), SoundSource.BLOCKS, this, this.getVolume(0.75F), 15F, 1.0F, 5);
                    this.audioLid.startSound();
                }
                this.audioLid.keepAlive();
            } else {
                if(this.audioLid != null) {
                    this.audioLid.stopSound();
                    this.audioLid = null;
                }
            }

            if((this.lid == 1 || this.lid == 0) && this.lid != this.prevLid && !(this.prevLid == 0 && this.lid == 1)) {
                NuclearTechMod.proxy.playLocalSound(this.getBlockPos().getCenter(), NtmSoundEvents.WGH_STOP.get(), SoundSource.BLOCKS, this.getVolume(1F), 1F);
            }

            if(this.isProgressing) {
                if(this.audioProgress == null || !this.audioProgress.isPlaying()) {
                    this.audioProgress = AudioWrapper.getLoopedSound(NtmSoundEvents.ELECTRIC_HUM_LOOP.get(), SoundSource.BLOCKS, this, this.getVolume(1.5F), 15F, 0.75F, 5);
                    this.audioProgress.startSound();
                }
                this.audioProgress.updatePitch(0.75F);
                this.audioProgress.keepAlive();
            } else {
                if(this.audioProgress != null) {
                    this.audioProgress.stopSound();
                    this.audioProgress = null;
                }
            }

            int x = this.getBlockPos().getX();
            int y = this.getBlockPos().getY();
            int z = this.getBlockPos().getZ();
            Player me = NuclearTechMod.proxy.me();
            boolean near = me != null && me.distanceToSqr(x + 0.5, y + 4, z + 0.5) < 50 * 50;

            // Smoke while the lid opens, flames while it closes over material (original :230-258).
            if(this.lid != this.prevLid && this.lid > this.prevLid && !(this.prevLid == 0 && this.lid == 1) && near) {
                CompoundTag data = new CompoundTag();
                data.putFloat("lift", 0.01F);
                data.putFloat("base", 0.5F);
                data.putFloat("max", 2F);
                data.putInt("life", 70 + this.level.random.nextInt(30));
                data.putBoolean("noWind", true);
                // The original writes "alphaMod", which its particle reads as "alpha" and therefore ignores; kept as is.
                data.putFloat("alphaMod", this.prevLid / this.lid);
                data.putInt("color", 0x000000);
                data.putFloat("strafe", 0.05F);
                for(int i = 0; i < 3; i++) {
                    ParticleUtil.addParticle(this.level, new NbtParticleOptions(NtmParticleTypes.COOLING_TOWER.get(), data), x + 0.5 + this.level.random.nextGaussian() * 0.5, y + 4, z + 0.5 + this.level.random.nextGaussian() * 0.5, 0F, 0F, 0F);
                }
            }

            if(this.lid != this.prevLid && this.lid < this.prevLid && this.lid > 0.5F && this.hasMaterial && near) {

                if(this.level.random.nextInt(5) == 0) {
                    CompoundTag flame = new CompoundTag();
                    // The original's maxAge; NEO's flame particle reads the age as "lifetime".
                    flame.putInt("lifetime", 50);
                    for(int i = 0; i < 2; i++) {
                        ParticleUtil.addParticle(this.level, new NbtParticleOptions(NtmParticleTypes.RBMK_FLAME.get(), flame), x + 0.5 + this.level.random.nextGaussian() * 0.5, y + 2.75, z + 0.5 + this.level.random.nextGaussian() * 0.5);
                    }
                }
            }
        }
    }

    /** Moves items from the input queue (25-29) to the main grid (5-24). */
    public void loadIngredients() {

        boolean markDirty = false;

        for(int q /* queue */ = 25; q < 30; q++) {
            if(this.slots.get(q).isEmpty()) continue;
            ArcFurnaceRecipe recipe = ArcFurnaceRecipes.getRecipe(this.slots.get(q));
            if(recipe == null) continue;
            int max = this.getMaxInputSize();
            // The original divides the input's maximum stack size by the output count (:272), so that a full grid stack
            // still fits its output in one stack.
            int recipeMax = this.slots.get(q).getMaxStackSize() / recipe.solidOutput.getCount();
            max = Math.min(max, recipeMax);
            // Intentional fix of the original: with a custom recipe whose output count exceeds the input's stack size the
            // original copies zero-size stacks into every empty grid slot; here such a queue entry is left alone.
            if(max <= 0) continue;

            // add to existing stacks
            for(int i /* ingredient */ = 5; i < 25; i++) {
                ItemStack ingredient = this.slots.get(i);
                if(ingredient.isEmpty()) continue;
                if(!ItemStack.isSameItemSameComponents(this.slots.get(q), ingredient)) continue;
                int toMove = Math.min(Math.min(ingredient.getMaxStackSize() - ingredient.getCount(), this.slots.get(q).getCount()), max - ingredient.getCount());
                if(toMove > 0) {
                    this.slots.get(q).shrink(toMove);
                    ingredient.grow(toMove);
                    markDirty = true;
                }
                if(this.slots.get(q).isEmpty()) break;
            }

            // add to empty slot
            if(!this.slots.get(q).isEmpty()) for(int i /* ingredient */ = 5; i < 25; i++) {
                if(!this.slots.get(i).isEmpty()) continue;
                int toMove = Math.min(max, this.slots.get(q).getCount());
                this.slots.set(i, this.slots.get(q).copyWithCount(toMove));
                this.slots.get(q).shrink(toMove);
                markDirty = true;
                if(this.slots.get(q).isEmpty()) break;
            }

            if(this.slots.get(q).isEmpty()) this.slots.set(q, ItemStack.EMPTY);
        }

        if(markDirty) this.setChanged();
    }

    public void decideElectrodeState() {
        for(int i = 0; i < 3; i++) {
            ItemStack stack = this.slots.get(i);

            if(!stack.isEmpty()) {
                if(isBurntElectrode(stack)) { this.electrodeStates[i] = ELECTRODE_DEPLETED; continue; }
                if(stack.getItem() instanceof ArcElectrodeItem) {
                    if(this.isProgressing || ArcElectrodeItem.getDurability(stack) > 0) this.electrodeStates[i] = ELECTRODE_USED;
                    else this.electrodeStates[i] = ELECTRODE_FRESH;
                    continue;
                }
            }
            this.electrodeStates[i] = ELECTRODE_NONE;
        }
    }

    /** The original's single arc_electrode_burnt item is one burnt item per material in NEO. */
    public static boolean isBurntElectrode(ItemStack stack) {
        Item item = stack.getItem();
        return item == NtmItems.ARC_ELECTRODE_GRAPHITE_BURNT.get() || item == NtmItems.ARC_ELECTRODE_LANTHANIUM_BURNT.get()
                || item == NtmItems.ARC_ELECTRODE_DESH_BURNT.get() || item == NtmItems.ARC_ELECTRODE_SATURNITE_BURNT.get();
    }

    /** Turns every grid stack with a recipe into its output, then wears all three electrodes (original :318-354). */
    public void process() {

        for(int i = 5; i < 25; i++) {
            ItemStack stack = this.slots.get(i);
            if(stack.isEmpty()) continue;
            ArcFurnaceRecipe recipe = ArcFurnaceRecipes.getRecipe(stack);
            if(recipe == null) continue;

            int amount = stack.getCount();
            ItemStack output = recipe.solidOutput.copy();
            output.setCount(output.getCount() * amount);
            this.slots.set(i, output);
        }

        for(int i = 0; i < 3; i++) {
            ItemStack electrode = this.slots.get(i);
            if(electrode.getItem() instanceof ArcElectrodeItem item && ArcElectrodeItem.damage(electrode)) {
                this.slots.set(i, new ItemStack(item.getBurnt()));
            }
        }
    }

    public boolean hasIngredients() {

        for(int i = 5; i < 25; i++) {
            if(this.slots.get(i).isEmpty()) continue;
            if(ArcFurnaceRecipes.getRecipe(this.slots.get(i)) != null) return true;
        }

        return false;
    }

    /** All three slots need a live electrode; a burnt one is a plain item and does not count. */
    public boolean hasElectrodes() {
        for(int i = 0; i < 3; i++) {
            if(!(this.slots.get(i).getItem() instanceof ArcElectrodeItem)) return false;
        }
        return true;
    }

    private static final int[] ACCESSIBLE_SLOTS = new int[] {
            0, 1, 2,
            5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24,
            25, 26, 27, 28, 29};

    @Override
    public int[] getSlotsForFace(Direction direction) {
        return ACCESSIBLE_SLOTS;
    }

    /** The original isItemValidForSlot, plus the battery and upgrade slots for the menu, as the arc welder. */
    @Override
    public boolean canPlaceItem(int slot, ItemStack stack) {
        if(slot < 3) return stack.getItem() instanceof ArcElectrodeItem;
        if(slot == 3) return stack.getItem() instanceof IBatteryItem;
        if(slot == 4) return stack.getItem() instanceof MachineUpgradeItem;
        return ArcFurnaceRecipes.getRecipe(stack) != null;
    }

    /** Automation fills the electrode slots and the queue only (original canInsertItem). */
    @Override
    public boolean canPlaceItemThroughFace(int slot, ItemStack stack, Direction direction) {
        if(slot < 3) return stack.getItem() instanceof ArcElectrodeItem;
        if(slot >= 25) return ArcFurnaceRecipes.getRecipe(stack) != null;
        return false;
    }

    /** Burnt electrodes once the lid is fully open, finished grid stacks while it is open, and queue items without a recipe. */
    @Override
    public boolean canTakeItemThroughFace(int slot, ItemStack stack, Direction direction) {
        if(slot < 3) return this.lid >= 1 && !(stack.getItem() instanceof ArcElectrodeItem);
        if(slot > 4 && slot < 25) return this.lid > 0 && ArcFurnaceRecipes.getRecipe(stack) == null;
        if(slot >= 25) return ArcFurnaceRecipes.getRecipe(stack) == null;
        return false;
    }

    /**
     * The six item and power proxies on the core layer, each paired with the side its port faces, as the original
     * getPorts (:549-564) and the extras of MachineArcFurnaceLarge.fillSpace (:59-64). MachineArcFurnaceBlock places its
     * extras from this list so the proxies and the connections cannot drift apart.
     */
    public static DirPos[] getPortProxies(BlockPos core, Direction dir) {
        Direction rot = dir.getClockWise(); // the original's getRotation(UP)

        return new DirPos[] {
                new DirPos(core.relative(dir, 2).relative(rot, 1), dir),
                new DirPos(core.relative(dir, 2).relative(rot, -1), dir),
                new DirPos(core.relative(rot, 2).relative(dir, 1), rot),
                new DirPos(core.relative(rot, 2).relative(dir, -1), rot),
                new DirPos(core.relative(rot, -2).relative(dir, 1), rot.getOpposite()),
                new DirPos(core.relative(rot, -2).relative(dir, -1), rot.getOpposite())
        };
    }

    /** One block outside each proxy in the direction its port faces (original PortDef.make). */
    public DirPos[] getConPos() {
        DirPos[] proxies = getPortProxies(this.worldPosition, this.getBlockState().getValue(DummyableBlock.FACING));
        DirPos[] conPos = new DirPos[proxies.length];

        for(int i = 0; i < proxies.length; i++) {
            Direction side = proxies[i].getDir();
            conPos[i] = new DirPos(proxies[i].makeCompat().relative(side), side);
        }

        return conPos;
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

    private void stopAudio() {
        if(this.audioLid != null) {
            this.audioLid.stopSound();
            this.audioLid = null;
        }
        if(this.audioProgress != null) {
            this.audioProgress.stopSound();
            this.audioProgress = null;
        }
    }

    @Override
    public long getPower() {
        return this.power;
    }

    @Override
    public void setPower(long power) {
        this.power = power;
    }

    @Override
    public long getMaxPower() {
        return MAX_POWER;
    }

    @Override
    public AbstractContainerMenu createMenu(int id, Inventory inventory, Player player) {
        return new MachineArcFurnaceMenu(id, inventory, this);
    }

    @Override
    public boolean canProvideInfo(UpgradeType type, int lvl, TooltipFlag flag) {
        return type == UpgradeType.SPEED;
    }

    @Override
    public void provideInfo(UpgradeType type, int lvl, List<Component> components, TooltipFlag flag) {
        components.add(IUpgradeInfoProvider.getStandardLabel(NtmBlocks.MACHINE_ARC_FURNACE.get()));
        if(type == UpgradeType.SPEED) {
            components.add(Component.translatable(KEY_DELAY, "-" + (100 - 100 / (lvl * 2 + 1)) + "%").withStyle(ChatFormatting.GREEN));
            components.add(Component.translatable(KEY_CONSUMPTION, "+" + ((int) Math.pow(5, lvl) * 100 - 100) + "%").withStyle(ChatFormatting.RED));
        }
    }

    @Override
    public HashMap<UpgradeType, Integer> getValidUpgrades() {
        HashMap<UpgradeType, Integer> upgrades = new HashMap<>();
        upgrades.put(UpgradeType.SPEED, 3);
        return upgrades;
    }

    @Override
    public void serialize(RegistryFriendlyByteBuf buf) {
        super.serialize(buf);
        buf.writeLong(this.power);
        buf.writeFloat(this.progress);
        buf.writeFloat(this.lid);
        buf.writeBoolean(this.isProgressing);
        buf.writeBoolean(this.hasMaterial);
        for(int i = 0; i < 3; i++) buf.writeByte(this.electrodeStates[i]);
    }

    @Override
    public void deserialize(RegistryFriendlyByteBuf buf) {
        super.deserialize(buf);
        this.power = buf.readLong();
        this.progress = buf.readFloat();
        this.syncLid = buf.readFloat();
        this.isProgressing = buf.readBoolean();
        this.hasMaterial = buf.readBoolean();
        for(int i = 0; i < 3; i++) this.electrodeStates[i] = buf.readByte();

        if(this.syncLid != 0 && this.syncLid != 1) this.approachNum = 2;
    }

    @Override
    protected void loadAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.loadAdditional(tag, registries);
        this.power = tag.getLong("power");
        this.progress = tag.getFloat("progress");
        this.lid = tag.getFloat("lid");
        this.delay = tag.getInt("delay");
    }

    @Override
    protected void saveAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.saveAdditional(tag, registries);
        tag.putLong("power", this.power);
        tag.putFloat("progress", this.progress);
        tag.putFloat("lid", this.lid);
        tag.putInt("delay", this.delay);
    }
}
