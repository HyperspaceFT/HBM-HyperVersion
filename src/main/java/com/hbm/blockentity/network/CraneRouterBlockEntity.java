package com.hbm.blockentity.network;

import com.hbm.blockentity.MachineBaseBlockEntity;
import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.interfaces.IControlReceiverFilter;
import com.hbm.inventory.menus.CraneRouterMenu;
import com.hbm.module.ModulePatternMatcher;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.HolderLookup;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.Tag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.chat.Component;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.AbstractContainerMenu;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.Vec3;

/**
 * Original TileEntityCraneRouter (the conveyor sorter). Its 30 slots are phantom filters, five per side: side s uses slots
 * 5s..5s+4, sides numbered down, up, north, south, west, east (Direction.get3DDataValue). Every side has a mode: off, whitelist,
 * blacklist or wildcard (:25-33). No slot is open to automation.
 */
public class CraneRouterBlockEntity extends MachineBaseBlockEntity implements IControlReceiverFilter {

    public static final int MODE_NONE = 0;
    public static final int MODE_WHITELIST = 1;
    public static final int MODE_BLACKLIST = 2;
    public static final int MODE_WILDCARD = 3;

    private static final int[] NO_SLOTS = new int[0];

    public final ModulePatternMatcher[] patterns = new ModulePatternMatcher[6];
    public int[] modes = new int[6];

    public CraneRouterBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.CRANE_ROUTER.get(), pos, state, 30);

        for(int i = 0; i < this.patterns.length; i++) {
            this.patterns[i] = new ModulePatternMatcher(5);
        }
    }

    @Override
    protected Component getDefaultName() {
        return Component.translatable("container.craneRouter");
    }

    /** Original :45-50: modes and filters are synced every tick. */
    @Override
    public void updateEntity() {
        if(this.level == null || this.level.isClientSide) return;
        this.networkPackNT(15);
    }

    @Override
    public void nextMode(int slot) {
        if(this.level != null) this.patterns[slot / 5].nextMode(this.level, this.slots.get(slot), slot % 5);
    }

    /** Original :94-100: a filter put in by hand gets its initial mode from the item's tags (ModulePatternMatcher.initPatternSmart). */
    public void initPattern(ItemStack stack, int slot) {
        if(this.level != null) this.patterns[slot / 5].initPatternSmart(this.level, stack, slot % 5);
    }

    /** Original :145-147. */
    @Override
    public int[] getFilterSlots() {
        return new int[] { 0, 30 };
    }

    /** The original base class opens no slot to automation (TileEntityMachineBase.java:135-138); NEO's base opens slot 0. */
    @Override
    public int[] getSlotsForFace(Direction side) {
        return NO_SLOTS;
    }

    @Override
    public boolean canPlaceItem(int slot, ItemStack stack) {
        return false;
    }

    /** The original only checks the distance (:125-128); NEO also requires the block entity to still be in its place. */
    @Override
    public boolean hasPermission(Player player) {
        if(this.level == null || this.level.getBlockEntity(this.worldPosition) != this) return false;
        return Vec3.atLowerCornerOf(this.worldPosition).distanceTo(player.position()) < 20D;
    }

    /**
     * Original :131-143: "toggle" cycles a side's mode, "slot" fills a filter slot. The original does not bound the side index a
     * client sends (GOAL31 decision 4); NEO ignores anything outside 0-5.
     */
    @Override
    public void receiveControl(CompoundTag tag) {
        if(tag.contains("toggle", Tag.TAG_ANY_NUMERIC)) {
            int side = tag.getInt("toggle");

            if(side >= 0 && side < 6) {
                this.modes[side]++;
                if(this.modes[side] > MODE_WILDCARD) this.modes[side] = MODE_NONE;
            }
        }

        if(tag.contains("slot") && this.level != null) this.setFilterContents(tag, this.level.registryAccess());
        this.setChanged();
    }

    @Override
    public void serialize(RegistryFriendlyByteBuf buf) {
        super.serialize(buf);
        for(ModulePatternMatcher pattern : this.patterns) pattern.serialize(buf);
        for(int mode : this.modes) buf.writeByte(mode);
    }

    @Override
    public void deserialize(RegistryFriendlyByteBuf buf) {
        super.deserialize(buf);
        for(ModulePatternMatcher pattern : this.patterns) pattern.deserialize(buf);
        for(int i = 0; i < 6; i++) this.modes[i] = buf.readByte();
    }

    /** Original :102-123: "pattern0".."pattern5" and the int array "modes"; a missing or malformed array reads as all off. */
    @Override
    protected void loadAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.loadAdditional(tag, registries);

        for(int i = 0; i < this.patterns.length; i++) {
            this.patterns[i].readFromNBT(tag.getCompound("pattern" + i));
        }

        int[] read = tag.getIntArray("modes");
        this.modes = isValidModes(read) ? read : new int[6];
    }

    @Override
    protected void saveAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.saveAdditional(tag, registries);

        for(int i = 0; i < this.patterns.length; i++) {
            CompoundTag pattern = new CompoundTag();
            this.patterns[i].writeToNBT(pattern);
            tag.put("pattern" + i, pattern);
        }

        tag.putIntArray("modes", this.modes);
    }

    private static boolean isValidModes(int[] modes) {
        if(modes.length != 6) return false;
        for(int mode : modes) if(mode < MODE_NONE || mode > MODE_WILDCARD) return false;
        return true;
    }

    /** Original :149-169: the filter items with their slot 0-29, and the six modes. */
    @Override
    public CompoundTag getSettings(Level level, BlockPos pos) {
        CompoundTag tag = new CompoundTag();
        tag.put("items", this.writeFilterItems(level.registryAccess()));
        tag.putIntArray("modes", this.modes.clone());
        return tag;
    }

    /**
     * Original :172-192, with its actual effect (GOAL31 decision 4): when the copy holds filter items and modes, only the side the
     * index picks is pasted, and its condition "slot > index * 5" always skips that side's first slot; each pasted slot advances its
     * mode once, then the six modes replace the router's. A copy without items (a router with an empty filter) or without modes (from
     * an extractor or a grabber) falls back to the filter interface's paste and keeps the six modes. The copied data comes from an
     * item a player can rewrite, so the router branch pastes nothing unless there are six modes of 0-3 and every entry's slot is
     * 0-29; entries whose item does not load are skipped.
     */
    @Override
    public void pasteSettings(CompoundTag tag, int index, Level level, Player player, BlockPos pos) {
        ListTag items = tag.getList("items", Tag.TAG_COMPOUND);

        if(!items.isEmpty() && tag.contains("modes")) {
            if(!tag.contains("modes", Tag.TAG_INT_ARRAY)) return;

            int[] pasted = tag.getIntArray("modes");
            if(!isValidModes(pasted)) return;

            for(int i = 0; i < items.size(); i++) {
                CompoundTag slotTag = items.getCompound(i);
                if(!slotTag.contains("slot", Tag.TAG_ANY_NUMERIC)) return;
                int slot = slotTag.getByte("slot");
                if(slot < 0 || slot >= 30) return;
            }

            for(int i = 0; i < items.size(); i++) {
                CompoundTag slotTag = items.getCompound(i);
                int slot = slotTag.getByte("slot");

                if(slot > index * 5 && slot < Math.min(index * 5 + 5, 30)) {
                    ItemStack stack = IControlReceiverFilter.readFilterStack(slotTag, level.registryAccess());
                    if(stack.isEmpty()) continue;

                    this.setItem(slot, stack);
                    this.nextMode(slot);
                }
            }

            this.modes = pasted.clone();
            this.setChanged();
        } else {
            this.pasteFilterItems(tag, level.registryAccess());
        }
    }

    /** Original :195-202: one entry per side, red, orange, yellow, green, blue, purple. */
    @Override
    public String[] infoForDisplay(Level level, BlockPos pos) {
        String[] options = new String[this.patterns.length];
        for(int i = 0; i < options.length; i++) options[i] = "copytool.pattern" + i;
        return options;
    }

    @Override
    public AbstractContainerMenu createMenu(int containerId, Inventory inventory, Player player) {
        return new CraneRouterMenu(containerId, inventory, this);
    }
}
