package com.hbm.blockentity.machine;

import api.hbm.energymk2.IBatteryItem;
import api.hbm.energymk2.IEnergyReceiverMK2;
import com.hbm.blockentity.MachineBaseBlockEntity;
import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.inventory.menus.MachineShredderMenu;
import com.hbm.inventory.recipes.ShredderRecipes;
import com.hbm.items.NtmItems;
import com.hbm.lib.Library;
import com.hbm.util.fauxpointtwelve.DirPos;
import com.hbm.sound.AudioWrapper;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.HolderLookup;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.chat.Component;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.AbstractContainerMenu;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.block.state.BlockState;

public class MachineShredderBlockEntity extends MachineBaseBlockEntity implements IEnergyReceiverMK2 {

    public static final int PROCESSING_SPEED = 60;
    public static final int STATUS_IDLE = 0;
    public static final int STATUS_RUNNING = 1;
    public static final int STATUS_MISSING_BLADES = 2;
    public static final int STATUS_BROKEN_BLADES = 3;
    public static final int STATUS_NO_POWER = 4;
    public static final int STATUS_OUTPUT_BLOCKED = 5;
    public static final int STATUS_INVALID_INPUT = 6;
    private static final int INPUT_START = 0;
    private static final int INPUT_END = 9;
    private static final int OUTPUT_START = 9;
    private static final int OUTPUT_END = 27;
    private static final int LEFT_BLADE = 27;
    private static final int RIGHT_BLADE = 28;
    private static final int BATTERY = 29;

    public long power;
    public long maxPower = 10_000L;
    public int progress;
    public int soundCycle;
    private int operatingStatus = STATUS_IDLE;
    private AudioWrapper audio;

    public MachineShredderBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.MACHINE_SHREDDER.get(), pos, state, 30);
    }

    @Override
    protected Component getDefaultName() {
        return Component.translatable("container.machine_shredder");
    }

    @Override
    public void updateEntity() {
        if(this.level == null) return;

        if(this.level.isClientSide) {
            if(this.operatingStatus == STATUS_RUNNING) {
                if(this.audio == null) {
                    this.audio = this.createAudioLoop();
                    if(this.audio != null) {
                        this.audio.startSound();
                    }
                } else if(!this.audio.isPlaying()) {
                    this.audio = this.rebootAudio(this.audio);
                }

                if(this.audio != null) {
                    this.audio.keepAlive();
                }
            } else if(this.audio != null) {
                this.audio.stopSound();
                this.audio = null;
            }
            return;
        }

        for(DirPos dirPos : this.getConPos()) {
            this.trySubscribe(this.level, dirPos);
        }

        long previousPower = this.power;
        int previousProgress = this.progress;
        int previousSoundCycle = this.soundCycle;
        this.power = this.getPower();
        this.operatingStatus = this.findOperatingStatus();

        if(this.operatingStatus == STATUS_RUNNING) {
            this.progress++;
            this.power -= 5L;

            if(this.progress >= PROCESSING_SPEED) {
                this.progress = 0;
                if(this.processItem()) this.damageBlades();
                this.setChanged();
            }

            this.soundCycle++;
            if(this.soundCycle >= 50) {
                this.soundCycle = 0;
            }
        } else {
            this.progress = 0;
            this.soundCycle = 0;
        }

        this.setPower(Library.chargeTEFromItems(this.slots, BATTERY, this.power, this.getMaxPower()));
        if(previousPower != this.power || previousProgress != this.progress || previousSoundCycle != this.soundCycle) {
            this.setChanged();
        }
        this.networkPackNT(25);
    }

    public int getOperatingStatus() {
        return this.operatingStatus;
    }

    private int findOperatingStatus() {
        if(this.getGearLeft() == 0 || this.getGearRight() == 0) return STATUS_MISSING_BLADES;
        if(this.getGearLeft() == 3 || this.getGearRight() == 3) return STATUS_BROKEN_BLADES;

        boolean hasInput = false;
        boolean hasResult = false;
        for(int i = INPUT_START; i < INPUT_END; i++) {
            ItemStack stack = this.slots.get(i);
            if(stack.isEmpty()) continue;
            hasInput = true;
            ItemStack result = this.getProcessResult(stack);
            if(result.isEmpty()) continue;
            hasResult = true;
            if(this.hasSpaceForResult(result)) return this.getPower() >= 5L ? STATUS_RUNNING : STATUS_NO_POWER;
        }

        if(!hasInput) return STATUS_IDLE;
        return hasResult ? STATUS_OUTPUT_BLOCKED : STATUS_INVALID_INPUT;
    }

    private ItemStack getProcessResult(ItemStack input) {
        if(input.isEmpty() || this.isBlade(input) || input.getItem() instanceof IBatteryItem) return ItemStack.EMPTY;
        return ShredderRecipes.getShredderResult(input);
    }

    private boolean processItem() {
        boolean processed = false;
        for(int inputSlot = INPUT_START; inputSlot < INPUT_END; inputSlot++) {
            ItemStack input = this.slots.get(inputSlot);
            if(input.isEmpty()) continue;

            // Recheck against outputs already reserved by earlier inputs in this round.
            ItemStack output = this.getProcessResult(input);
            if(!this.hasSpaceForResult(output)) continue;
            int remaining = output.getCount();

            for(int outSlot = OUTPUT_START; outSlot < OUTPUT_END && remaining > 0; outSlot++) {
                ItemStack current = this.slots.get(outSlot);
                if(current.isEmpty()) continue;
                if(!ItemStack.isSameItemSameComponents(current, output)) continue;

                int space = Math.min(this.getMaxStackSize(), current.getMaxStackSize()) - current.getCount();
                if(space <= 0) continue;

                int moved = Math.min(space, remaining);
                current.grow(moved);
                remaining -= moved;
            }

            for(int outSlot = OUTPUT_START; outSlot < OUTPUT_END && remaining > 0; outSlot++) {
                ItemStack current = this.slots.get(outSlot);
                if(!current.isEmpty()) continue;

                int moved = Math.min(remaining, Math.min(this.getMaxStackSize(), output.getMaxStackSize()));
                ItemStack placed = output.copy();
                placed.setCount(moved);
                this.slots.set(outSlot, placed);
                remaining -= moved;
            }

            input.shrink(1);
            if(input.isEmpty()) {
                this.slots.set(inputSlot, ItemStack.EMPTY);
            }
            processed = true;
        }
        return processed;
    }

    private void damageBlades() {
        for(int slot : new int[] { LEFT_BLADE, RIGHT_BLADE }) {
            ItemStack stack = this.slots.get(slot);
            if(stack.isDamageableItem()) {
                stack.setDamageValue(stack.getDamageValue() + 1);
            }
        }
    }

    private boolean hasSpaceForResult(ItemStack result) {
        if(result.isEmpty()) return false;

        long spaceLeft = 0;

        for(int outSlot = OUTPUT_START; outSlot < OUTPUT_END; outSlot++) {
            ItemStack current = this.slots.get(outSlot);
            if(current.isEmpty()) {
                spaceLeft += Math.min(this.getMaxStackSize(), result.getMaxStackSize());
            } else if(ItemStack.isSameItemSameComponents(current, result)) {
                spaceLeft += Math.max(0, Math.min(this.getMaxStackSize(), current.getMaxStackSize()) - current.getCount());
            }
            if(spaceLeft >= result.getCount()) return true;
        }

        return spaceLeft >= result.getCount();
    }

    public int getGearLeft() {
        return this.getGear(LEFT_BLADE);
    }

    public int getGearRight() {
        return this.getGear(RIGHT_BLADE);
    }

    private int getGear(int slot) {
        ItemStack stack = this.slots.get(slot);
        if(stack.isEmpty()) return 0;
        if(stack.getItem() != NtmItems.BLADES_STEEL.get() && stack.getItem() != NtmItems.BLADES_TITANIUM.get() && stack.getItem() != NtmItems.BLADES_DESH.get()) return 0;
        if(!stack.isDamageableItem()) return 1;
        if(stack.getDamageValue() < stack.getMaxDamage() / 2) return 1;
        if(stack.getDamageValue() < stack.getMaxDamage()) return 2;
        return 3;
    }

    public DirPos[] getConPos() {
        BlockPos pos = this.getBlockPos();
        return new DirPos[] {
                new DirPos(pos.getX() + 1, pos.getY(), pos.getZ(), Direction.EAST),
                new DirPos(pos.getX() - 1, pos.getY(), pos.getZ(), Direction.WEST),
                new DirPos(pos.getX(), pos.getY(), pos.getZ() + 1, Direction.SOUTH),
                new DirPos(pos.getX(), pos.getY(), pos.getZ() - 1, Direction.NORTH),
                new DirPos(pos.getX(), pos.getY() + 1, pos.getZ(), Direction.UP),
                new DirPos(pos.getX(), pos.getY() - 1, pos.getZ(), Direction.DOWN)
        };
    }

    public int getProgressScaled(int pixels) {
        return this.progress * pixels / PROCESSING_SPEED;
    }

    public int getPowerScaled(int pixels) {
        return (int) ((double) this.getPower() / Math.max(this.getMaxPower(), 1L) * pixels);
    }

    @Override
    public boolean canPlaceItem(int slot, ItemStack stack) {
        if(slot >= INPUT_START && slot < INPUT_END) {
            return !this.getProcessResult(stack).isEmpty();
        }

        if(slot == LEFT_BLADE || slot == RIGHT_BLADE) {
            return this.isBlade(stack);
        }

        if(slot == BATTERY) {
            return stack.getItem() instanceof IBatteryItem;
        }

        return false;
    }

    @Override
    public boolean canPlaceItemThroughFace(int index, ItemStack stack, Direction direction) {
        if(index == BATTERY || !this.canPlaceItem(index, stack)) return false;
        if(index == LEFT_BLADE || index == RIGHT_BLADE) return true;
        ItemStack current = this.slots.get(index);
        if(current.isEmpty()) return true;

        // Fill empty input positions before stacking, so automation can use all nine per round.
        for(int slot = INPUT_START; slot < INPUT_END; slot++) {
            ItemStack other = this.slots.get(slot);
            if(other.isEmpty()) return false;
            if(ItemStack.isSameItemSameComponents(other, stack) && other.getCount() < current.getCount()) return false;
        }
        return true;
    }

    @Override
    public boolean canTakeItemThroughFace(int index, ItemStack stack, Direction direction) {
        if(index >= OUTPUT_START && index < OUTPUT_END) return true;
        if((index == LEFT_BLADE || index == RIGHT_BLADE) && stack.isDamageableItem() && stack.getDamageValue() >= stack.getMaxDamage()) return true;
        return false;
    }

    @Override
    public int[] getSlotsForFace(Direction direction) {
        return new int[] {
                0, 1, 2, 3, 4, 5, 6, 7, 8,
                9, 10, 11, 12, 13, 14, 15, 16, 17,
                18, 19, 20, 21, 22, 23, 24, 25, 26,
                27, 28, 29
        };
    }

    @Override
    protected void loadAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.loadAdditional(tag, registries);
        this.power = tag.getLong("power");
        this.maxPower = tag.contains("maxPower") && tag.getLong("maxPower") > 0 ? tag.getLong("maxPower") : 10_000L;
        this.power = this.getPower();
        this.progress = Math.max(0, Math.min(tag.getInt("progress"), PROCESSING_SPEED - 1));
        this.soundCycle = Math.max(0, Math.min(tag.getInt("soundCycle"), 49));
        this.operatingStatus = STATUS_IDLE;
    }

    @Override
    protected void saveAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.saveAdditional(tag, registries);
        tag.putLong("power", this.power);
        tag.putLong("maxPower", this.maxPower);
        tag.putInt("progress", this.progress);
        tag.putInt("soundCycle", this.soundCycle);
    }

    @Override
    public void serialize(RegistryFriendlyByteBuf buf) {
        super.serialize(buf);
        buf.writeLong(this.power);
        buf.writeLong(this.maxPower);
        buf.writeInt(this.progress);
        buf.writeInt(this.soundCycle);
        buf.writeInt(this.operatingStatus);
    }

    @Override
    public void deserialize(RegistryFriendlyByteBuf buf) {
        super.deserialize(buf);
        this.power = buf.readLong();
        this.maxPower = buf.readLong();
        this.progress = buf.readInt();
        this.soundCycle = buf.readInt();
        this.operatingStatus = buf.readInt();
    }

    @Override
    public long getPower() {
        return Math.max(Math.min(this.power, this.getMaxPower()), 0L);
    }

    @Override
    public void setPower(long power) {
        long clamped = Math.max(0L, Math.min(power, this.getMaxPower()));
        if(this.power != clamped) {
            this.power = clamped;
            this.setChanged();
        }
    }

    @Override
    public long transferPower(long power) {
        if(power <= 0L) return power;
        // Subtract capacity before adding, including for unusually large provider requests.
        long accepted = Math.min(power, this.getMaxPower() - this.getPower());
        this.setPower(this.getPower() + accepted);
        return power - accepted;
    }

    @Override
    public long getMaxPower() {
        return Math.max(0L, this.maxPower);
    }

    @Override
    public AbstractContainerMenu createMenu(int id, Inventory inventory, Player player) {
        return new MachineShredderMenu(id, inventory, this);
    }

    @Override
    public AudioWrapper createAudioLoop() {
        return AudioWrapper.getLoopedSound(SoundEvents.MINECART_RIDING, SoundSource.BLOCKS, this, 1.0F, 15F, 0.65F, 20);
    }

    @Override
    public void onChunkUnloaded() {
        super.onChunkUnloaded();
        if(this.audio != null) {
            this.audio.stopSound();
            this.audio = null;
        }
    }

    @Override
    public void setRemoved() {
        super.setRemoved();
        if(this.audio != null) {
            this.audio.stopSound();
            this.audio = null;
        }
    }

    public boolean hasPermission(Player player) {
        return this.stillValid(player);
    }

    private boolean isBlade(ItemStack stack) {
        return stack.getItem() == NtmItems.BLADES_STEEL.get()
                || stack.getItem() == NtmItems.BLADES_TITANIUM.get()
                || stack.getItem() == NtmItems.BLADES_DESH.get();
    }
}
