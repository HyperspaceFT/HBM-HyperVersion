package com.hbm.blockentity.machine;

import api.hbm.energymk2.IBatteryItem;
import api.hbm.energymk2.IEnergyReceiverMK2;
import com.hbm.blockentity.IUpgradeInfoProvider;
import com.hbm.blockentity.MachineBaseBlockEntity;
import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.blocks.NtmBlocks;
import com.hbm.blocks.machine.MachineElectricFurnaceBlock;
import com.hbm.handler.pollution.PollutionHandler;
import com.hbm.handler.pollution.PollutionHandler.PollutionType;
import com.hbm.inventory.UpgradeManagerNT;
import com.hbm.inventory.menus.MachineElectricFurnaceMenu;
import com.hbm.items.machine.MachineUpgradeItem;
import com.hbm.items.machine.MachineUpgradeItem.UpgradeType;
import com.hbm.lib.Library;
import com.hbm.util.fauxpointtwelve.DirPos;
import net.minecraft.ChatFormatting;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.HolderLookup;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.chat.Component;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.AbstractContainerMenu;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.item.crafting.RecipeHolder;
import net.minecraft.world.item.crafting.RecipeManager;
import net.minecraft.world.item.crafting.RecipeType;
import net.minecraft.world.item.crafting.SingleRecipeInput;
import net.minecraft.world.item.crafting.SmeltingRecipe;
import net.minecraft.world.level.block.state.BlockState;

import java.util.HashMap;
import java.util.List;
import java.util.Optional;

public class MachineElectricFurnaceBlockEntity extends MachineBaseBlockEntity implements IEnergyReceiverMK2, IUpgradeInfoProvider {

    // HOLY FUCKING SHIT I SPENT 5 DAYS ON THIS SHITFUCK CLASS FILE
    // thanks Martin, vaer and Bob for the help

    public static final int SLOT_BATTERY = 0;
    public static final int SLOT_INPUT = 1;
    public static final int SLOT_OUTPUT = 2;
    public static final int SLOT_UPGRADE = 3;
    public static final long MAX_POWER = 100_000L;
    public static final int BASE_PROCESS_TIME = 100;
    public static final int BASE_CONSUMPTION = 50;
    /** Ticks without processing after the buffer drops below one tick's consumption. */
    public static final int COOLDOWN = 20;

    private static final int[] SLOTS_IO = new int[] { SLOT_BATTERY, SLOT_INPUT, SLOT_OUTPUT };

    public final UpgradeManagerNT upgradeManager = new UpgradeManagerNT(this);
    public long power;
    public int progress;
    public int maxProgress = BASE_PROCESS_TIME;
    public int consumption = BASE_CONSUMPTION;
    private int cooldown = 0;

    private final RecipeManager.CachedCheck<SingleRecipeInput, SmeltingRecipe> smeltingCheck = RecipeManager.createCheck(RecipeType.SMELTING);

    public MachineElectricFurnaceBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.MACHINE_ELECTRIC_FURNACE.get(), pos, state, 4);
    }

    @Override
    protected Component getDefaultName() {
        return Component.translatable("container.electricFurnace");
    }

    @Override
    public void updateEntity() {
        if(this.level == null || this.level.isClientSide) return;

        boolean markDirty = false;

        for(DirPos dirPos : this.getConPos()) {
            this.trySubscribe(this.level, dirPos);
        }

        if(this.cooldown > 0) {
            this.cooldown--;
        }

        this.power = Library.chargeTEFromItems(this.slots, SLOT_BATTERY, this.getPower(), this.getMaxPower());

        this.consumption = BASE_CONSUMPTION;
        this.maxProgress = BASE_PROCESS_TIME;

        this.upgradeManager.checkSlots(this.slots, SLOT_UPGRADE, SLOT_UPGRADE);

        int speedLevel = this.upgradeManager.getLevel(UpgradeType.SPEED);
        int powerLevel = this.upgradeManager.getLevel(UpgradeType.POWER);

        this.maxProgress -= speedLevel * 25;
        this.consumption += speedLevel * 50;
        this.maxProgress += powerLevel * 10;
        this.consumption -= powerLevel * 15;

        if(!this.hasPower()) {
            this.cooldown = COOLDOWN;
        }

        if(this.hasPower() && this.canProcess()) {
            this.progress++;

            this.power -= this.consumption;

            if(this.level.getGameTime() % 20 == 0) {
                PollutionHandler.incrementPollution(this.level, this.worldPosition, PollutionType.SOOT, PollutionHandler.SOOT_PER_SECOND);
            }

            if(this.progress >= this.maxProgress) {
                this.progress = 0;
                this.processItem();
                markDirty = true;
            }
        } else {
            // Losing power or a blocked output loses the progress, as upstream.
            this.progress = 0;
        }

        // Upstream skips the block update only while it is about to start the next item, so it does not flicker between items.
        boolean trigger = true;

        if(this.hasPower() && this.canProcess() && this.progress == 0) {
            trigger = false;
        }

        if(trigger) {
            markDirty = true;
            this.setLit(this.progress > 0);
        }

        this.networkPackNT(50);

        if(markDirty) {
            this.setChanged();
        }
    }

    /** Upstream swaps between the _off and _on blocks; NEO keeps one block and its block entity and flips LIT. */
    private void setLit(boolean lit) {
        if(this.level == null) return;
        BlockState state = this.getBlockState();
        if(!state.hasProperty(MachineElectricFurnaceBlock.LIT) || state.getValue(MachineElectricFurnaceBlock.LIT) == lit) return;
        this.level.setBlock(this.worldPosition, state.setValue(MachineElectricFurnaceBlock.LIT, lit), 3);
    }

    public boolean hasPower() {
        return this.power >= this.consumption;
    }

    public boolean canProcess() {
        ItemStack input = this.slots.get(SLOT_INPUT);
        if(input.isEmpty() || this.cooldown > 0) return false;

        ItemStack result = this.getSmeltingResult(input);
        if(result.isEmpty()) return false;

        ItemStack output = this.slots.get(SLOT_OUTPUT);
        if(output.isEmpty()) return true;
        if(!ItemStack.isSameItemSameComponents(output, result)) return false;

        // Upstream only checks for one free spot; NEO also keeps multi-item results within the stack size.
        return output.getCount() + result.getCount() <= Math.min(output.getMaxStackSize(), this.getMaxStackSize());
    }

    private void processItem() {
        if(!this.canProcess()) return;

        ItemStack result = this.getSmeltingResult(this.slots.get(SLOT_INPUT));
        ItemStack output = this.slots.get(SLOT_OUTPUT);

        if(output.isEmpty()) {
            this.slots.set(SLOT_OUTPUT, result.copy());
        } else {
            output.grow(result.getCount());
        }

        this.slots.get(SLOT_INPUT).shrink(1);
    }

    /** The Minecraft furnace result for one item, as upstream's FurnaceRecipes lookup; empty without a level or recipe. */
    public ItemStack getSmeltingResult(ItemStack stack) {
        if(this.level == null || stack.isEmpty()) return ItemStack.EMPTY;
        SingleRecipeInput input = new SingleRecipeInput(stack);
        Optional<RecipeHolder<SmeltingRecipe>> recipe = this.smeltingCheck.getRecipeFor(input, this.level);
        return recipe.map(holder -> holder.value().assemble(input, this.level.registryAccess())).orElse(ItemStack.EMPTY);
    }

    public int getProgressScaled(int pixels) {
        return this.progress * pixels / Math.max(this.maxProgress, 1);
    }

    public long getPowerScaled(long pixels) {
        return this.power * pixels / MAX_POWER;
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

    @Override
    public boolean canPlaceItem(int slot, ItemStack stack) {
        if(slot == SLOT_BATTERY) return stack.getItem() instanceof IBatteryItem;
        if(slot == SLOT_INPUT) return !this.getSmeltingResult(stack).isEmpty();
        // Upstream's upgrade slot only accepts upgrades in the GUI; automation cannot reach it (see getSlotsForFace).
        if(slot == SLOT_UPGRADE) return stack.getItem() instanceof MachineUpgradeItem;
        return false;
    }

    @Override
    public boolean canTakeItemThroughFace(int index, ItemStack stack, Direction direction) {
        return index == SLOT_OUTPUT;
    }

    @Override
    public int[] getSlotsForFace(Direction direction) {
        return SLOTS_IO;
    }

    @Override
    protected void loadAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.loadAdditional(tag, registries);
        this.power = Math.max(0L, Math.min(tag.getLong("power"), MAX_POWER));
        this.progress = Math.max(0, tag.getInt("progress"));
    }

    @Override
    protected void saveAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.saveAdditional(tag, registries);
        tag.putLong("power", this.power);
        tag.putInt("progress", this.progress);
    }

    @Override
    public void serialize(RegistryFriendlyByteBuf buf) {
        super.serialize(buf);
        buf.writeLong(this.power);
        buf.writeInt(this.maxProgress);
        buf.writeInt(this.progress);
        // Not synced upstream; the screen's hasPower() needs it once upgrades change the consumption.
        buf.writeInt(this.consumption);
    }

    @Override
    public void deserialize(RegistryFriendlyByteBuf buf) {
        super.deserialize(buf);
        this.power = buf.readLong();
        this.maxProgress = buf.readInt();
        this.progress = buf.readInt();
        this.consumption = buf.readInt();
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
        return new MachineElectricFurnaceMenu(id, inventory, this);
    }

    @Override
    public boolean canProvideInfo(UpgradeType type, int lvl, TooltipFlag flag) {
        return type == UpgradeType.SPEED || type == UpgradeType.POWER;
    }

    @Override
    public void provideInfo(UpgradeType type, int lvl, List<Component> components, TooltipFlag flag) {
        components.add(IUpgradeInfoProvider.getStandardLabel(NtmBlocks.MACHINE_ELECTRIC_FURNACE.get()));
        if(type == UpgradeType.SPEED) {
            components.add(Component.translatable(KEY_DELAY, "-" + (lvl * 25) + "%").withStyle(ChatFormatting.GREEN));
            components.add(Component.translatable(KEY_CONSUMPTION, "+" + (lvl * 100) + "%").withStyle(ChatFormatting.RED));
        }
        if(type == UpgradeType.POWER) {
            components.add(Component.translatable(KEY_CONSUMPTION, "-" + (lvl * 30) + "%").withStyle(ChatFormatting.GREEN));
            components.add(Component.translatable(KEY_DELAY, "+" + (lvl * 10) + "%").withStyle(ChatFormatting.RED));
        }
    }

    @Override
    public HashMap<UpgradeType, Integer> getValidUpgrades() {
        HashMap<UpgradeType, Integer> upgrades = new HashMap<>();
        upgrades.put(UpgradeType.SPEED, 3);
        upgrades.put(UpgradeType.POWER, 3);
        return upgrades;
    }
}
