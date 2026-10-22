package com.hbm.blockentity.machine.rbmk;

import com.hbm.blockentity.MachineBaseBlockEntity;
import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.blocks.machine.rbmk.RBMKBaseBlock;
import com.hbm.interfaces.IControlReceiver;
import com.hbm.interfaces.ICopiable;
import com.hbm.inventory.menus.RBMKAutoloaderMenu;
import com.hbm.items.machine.RBMKRodItem;
import com.hbm.main.NuclearTechMod;
import com.hbm.particle.NtmParticleTypes;
import com.hbm.particle.vanilla.NbtParticleOptions;
import com.hbm.registry.NtmSoundEvents;
import com.hbm.sound.AudioWrapper;
import com.hbm.util.particle.ParticleUtil;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.HolderLookup;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.chat.Component;
import net.minecraft.sounds.SoundSource;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.AbstractContainerMenu;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.AABB;

/**
 * Original TileEntityRBMKAutoloader: sits on top of a fuel channel and swaps its rod. Slots 0-8 hold fresh rods, slots 9-17 take
 * the spent ones. Every 20 ticks a loader that is not extending checks the channel below (as the original :68, also while the piston
 * is still rising and during the hold at the bottom, where a positive check reverses the stroke); when a rod can be inserted it lowers
 * the piston, swaps the rods at the bottom and rises again, waiting 40 ticks at either end.
 */
public class RBMKAutoloaderBlockEntity extends MachineBaseBlockEntity implements IControlReceiver, ICopiable {

    private static final int[] SLOTS = new int[] {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17};
    private static final int[] NO_SLOTS = new int[0];

    public double piston;
    public double renderPiston;
    public double lastPiston;
    private double syncPiston;
    private int turnProgress;
    private boolean isRetracting = true;
    private int delay = 0;

    /** Piston travel per tick. The original speed (:37) is a mutable public static that nothing writes; final here. */
    public static final double SPEED = 0.005D;

    public int cycle = 50;

    private AudioWrapper audioLift;

    public RBMKAutoloaderBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.RBMK_AUTOLOADER.get(), pos, state, 18);
    }

    @Override
    protected Component getDefaultName() {
        return Component.translatable("container.rbmkAutoloader");
    }

    /** Original updateEntity (:53-173). */
    @Override
    public void updateEntity() {
        if(this.level == null) return;

        if(!this.level.isClientSide) {

            double prevPiston = this.piston;
            boolean prevRetracting = this.isRetracting;
            int prevDelay = this.delay;

            if(delay > 0) delay--;

            if(delay <= 0 && this.isRetracting && this.piston > 0D) {
                this.piston -= SPEED;
                if(this.piston <= 0) {
                    this.piston = 0;
                    this.delay = 40;
                }
            }

            // check for connected fuel rod and decide whether to begin working
            if(isRetracting && this.level.getGameTime() % 20 == 0 && this.hasFuel() && this.hasSpace()) {
                RBMKRodBlockEntity rod = this.getRodBelow();
                if(rod != null && rod.coldEnoughForAutoloader()) {
                    ItemStack loaded = rod.slots.get(0);
                    if(loaded.isEmpty() || (loaded.getItem() instanceof RBMKRodItem && RBMKRodItem.getEnrichment(loaded) * 100 < cycle)) {
                        this.isRetracting = false;
                    }
                }
            }

            if(delay <= 0 && !this.isRetracting && this.piston < 1D) {
                this.piston += SPEED;
                if(this.piston >= 1) {
                    this.piston = 1;
                    this.delay = 40;
                }
            }

            // once the piston is fully extended
            // Upstream-shared: if the fuel channel below is gone by now, nothing happens and the piston stays extended.
            if(!isRetracting && this.piston >= 1D) {
                this.piston = 1D;

                RBMKRodBlockEntity rod = this.getRodBelow();
                if(rod != null) {
                    // try to take out the old fuel rod
                    if(!rod.slots.get(0).isEmpty() && this.hasSpace()) {
                        for(int i = 9; i < 18; i++) {
                            if(slots.get(i).isEmpty()) {
                                slots.set(i, rod.slots.get(0).copy());
                                rod.slots.set(0, ItemStack.EMPTY);
                                break;
                            }
                        }
                    }
                    // if there's space, try and insert a new fuel rod
                    if(rod.slots.get(0).isEmpty()) {
                        for(int i = 0; i < 9; i++) {
                            ItemStack stack = slots.get(i);
                            if(!stack.isEmpty() && stack.getItem() instanceof RBMKRodItem && RBMKRodItem.getEnrichment(stack) * 100 >= cycle) {
                                rod.slots.set(0, stack.copy());
                                slots.set(i, ItemStack.EMPTY);
                                break;
                            }
                        }
                    }

                    // NEO addition: the direct slot writes above bypass setItem, so both block entities are marked for saving here.
                    rod.setChanged();
                    this.setChanged();

                    this.isRetracting = true;
                    this.delay = 40;
                }
            }

            // NEO addition: 1.7.10 saved every tile entity of a chunk; here the saved piston, ret and delay only persist when marked.
            if(this.piston != prevPiston || this.isRetracting != prevRetracting || this.delay != prevDelay) this.setChanged();

            this.networkPackNT(100);
        } else {

            this.lastPiston = this.renderPiston;

            if(this.turnProgress > 0) {
                this.renderPiston = this.renderPiston + ((this.syncPiston - this.renderPiston) / (double) this.turnProgress);
                --this.turnProgress;
            } else {
                this.renderPiston = this.syncPiston;
            }

            if(this.renderPiston > 0.01 && this.renderPiston < 0.99) {
                if(this.audioLift == null || !this.audioLift.isPlaying()) {
                    this.audioLift = AudioWrapper.getLoopedSound(NtmSoundEvents.WGH_START.get(), SoundSource.BLOCKS, this, this.getVolume(0.75F), 25F, 1.0F, 5);
                    this.audioLift.startSound();
                }
                this.audioLift.updateVolume(this.getVolume(0.75F));
                this.audioLift.keepAlive();
            } else {
                if(this.audioLift != null) {
                    this.audioLift.stopSound();
                    this.audioLift = null;
                    NuclearTechMod.proxy.playLocalSound(this.getBlockPos().getX(), this.getBlockPos().getY(), this.getBlockPos().getZ(), NtmSoundEvents.WGH_STOP.get(), SoundSource.BLOCKS, this.getVolume(2F), 1F);
                }
            }

            if(this.renderPiston > 0.99) {
                int x = this.getBlockPos().getX();
                int y = this.getBlockPos().getY();
                int z = this.getBlockPos().getZ();

                CompoundTag data = new CompoundTag();
                data.putFloat("lift", 0F);
                data.putFloat("base", 0.25F);
                data.putFloat("max", 1.5F);
                data.putInt("life", 70 + this.level.random.nextInt(30));
                data.putBoolean("noWind", true);
                // The original writes "alphaMod", which its particle reads as "alpha" and therefore ignores; kept as is.
                data.putFloat("alphaMod", 2F);
                data.putFloat("strafe", 0.05F);
                // As the original (:164-170), the position is drawn once and shared by all three particles.
                double posX = x + 0.5 + this.level.random.nextGaussian() * 0.125;
                double posZ = z + 0.5 + this.level.random.nextGaussian() * 0.125;
                for(int i = 0; i < 3; i++) {
                    ParticleUtil.addParticle(this.level, new NbtParticleOptions(NtmParticleTypes.COOLING_TOWER.get(), data), posX, y + 0.25, posZ, 0F, 0F, 0F);
                }
            }
        }
    }

    /**
     * The fuel channel directly below, through the core of its column. NEO-defensive: the original (:69-73, :96-100) has no null
     * check on findCore.
     */
    private RBMKRodBlockEntity getRodBelow() {
        BlockPos below = this.worldPosition.below();
        if(this.level.getBlockState(below).getBlock() instanceof RBMKBaseBlock base) {
            BlockPos core = base.findCore(this.level, below);
            if(core != null && this.level.getBlockEntity(core) instanceof RBMKRodBlockEntity rod) return rod;
        }
        return null;
    }

    /** Original :175-184. */
    public boolean hasFuel() {
        for(int i = 0; i < 9; i++) {
            ItemStack stack = slots.get(i);
            if(!stack.isEmpty() && stack.getItem() instanceof RBMKRodItem && RBMKRodItem.getEnrichment(stack) * 100 >= cycle) {
                return true;
            }
        }

        return false;
    }

    /** Original :186-189. */
    public boolean hasSpace() {
        for(int i = 9; i < 18; i++) if(slots.get(i).isEmpty()) return true;
        return false;
    }

    public boolean isRetracting() {
        return this.isRetracting;
    }

    public int getDelay() {
        return this.delay;
    }

    @Override
    public void serialize(RegistryFriendlyByteBuf buf) {
        super.serialize(buf);
        buf.writeDouble(this.piston);
        buf.writeInt(this.cycle);
    }

    @Override
    public void deserialize(RegistryFriendlyByteBuf buf) {
        super.deserialize(buf);
        this.syncPiston = buf.readDouble();
        this.cycle = buf.readInt();

        this.turnProgress = 2;
    }

    // Original isItemValidForSlot, getAccessibleSlotsFromSide and canExtractItem (:207-220); insertion through a face asks
    // canPlaceItem (MachineBaseBlockEntity.canPlaceItemThroughFace). Automation only reaches the slots while the piston is up.
    @Override
    public boolean canPlaceItem(int i, ItemStack stack) {
        return i < 9 && stack.getItem() instanceof RBMKRodItem && RBMKRodItem.getEnrichment(stack) * 100 >= cycle;
    }

    @Override
    public int[] getSlotsForFace(Direction direction) {
        return this.piston <= 0 ? SLOTS : NO_SLOTS;
    }

    @Override
    public boolean canTakeItemThroughFace(int i, ItemStack stack, Direction direction) {
        return i >= 9;
    }

    @Override
    protected void loadAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.loadAdditional(tag, registries);
        this.piston = tag.getDouble("piston");
        this.isRetracting = tag.getBoolean("ret");
        this.delay = tag.getInt("delay");
        this.cycle = tag.getInt("cycle");
    }

    @Override
    protected void saveAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.saveAdditional(tag, registries);
        tag.putDouble("piston", this.piston);
        tag.putBoolean("ret", this.isRetracting);
        tag.putInt("delay", this.delay);
        tag.putInt("cycle", this.cycle);
    }

    /** Original getRenderBoundingBox (:242-247). */
    public AABB getRenderBoundingBox() {
        BlockPos pos = this.getBlockPos();
        return new AABB(pos.getX(), pos.getY(), pos.getZ(), pos.getX() + 1, pos.getY() + 9, pos.getZ() + 1);
    }

    /** Original isUseableByPlayer (TileEntityMachineBase.java:81-92): this block entity still in place and within 12 blocks of its centre. */
    @Override
    public boolean stillValid(Player player) {
        if(this.level == null || this.level.getBlockEntity(this.worldPosition) != this) return false;
        return player.distanceToSqr(this.worldPosition.getX() + 0.5D, this.worldPosition.getY() + 0.5D, this.worldPosition.getZ() + 0.5D) <= 12D * 12D;
    }

    @Override
    public boolean hasPermission(Player player) {
        return this.stillValid(player);
    }

    /** Original receiveControl (:260-266); server side. */
    @Override
    public void receiveControl(CompoundTag data) {
        if(data.contains("minus") && this.cycle > 5) this.cycle -= 5;
        if(data.contains("plus") && this.cycle < 95) this.cycle += 5;
        this.cycle = Mth.clamp(this.cycle, 5, 95);
        this.setChanged();
    }

    @Override
    public AbstractContainerMenu createMenu(int containerId, Inventory inventory, Player player) {
        return new RBMKAutoloaderMenu(containerId, inventory, this);
    }

    /** Original getSettings / pasteSettings (:279-291). */
    @Override
    public CompoundTag getSettings(Level world, BlockPos pos) {
        CompoundTag data = new CompoundTag();
        data.putInt("cycle", cycle);
        return data;
    }

    @Override
    public void pasteSettings(CompoundTag nbt, int index, Level world, Player player, BlockPos pos) {
        if(nbt.contains("cycle")) {
            this.cycle = Mth.clamp(nbt.getInt("cycle"), 5, 95);
            // NEO addition (review R1): mark the pasted threshold for saving, as receiveControl does.
            this.setChanged();
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

    private void stopAudio() {
        if(this.audioLift != null) {
            this.audioLift.stopSound();
            this.audioLift = null;
        }
    }
}
