package com.hbm.blockentity.machine;

import com.hbm.blockentity.MachineBaseBlockEntity;
import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.inventory.material.Mats;
import com.hbm.inventory.material.NTMMaterial;
import com.hbm.inventory.recipes.CopperCastingRecipes;
import com.hbm.items.CopperScrapsItem;
import com.hbm.items.NtmItems;
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
import net.minecraft.world.level.block.state.BlockState;

/** Small cast-plate, Dura ingot and tungsten blade molds: reusable molds and one output at a time. */
public class FoundryMoldBlockEntity extends MachineBaseBlockEntity {
    public int amount;
    public int cooloff = 200;
    public NTMMaterial type;

    public FoundryMoldBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.FOUNDRY_MOLD.get(), pos, state, 2);
    }

    @Override protected Component getDefaultName() { return Component.translatable("block.hbmsntm.foundry_mold"); }
    private boolean hasPlateMold() { return this.slots.get(0).is(NtmItems.MOLD_PLATE_CAST.get()); }
    private boolean hasIngotMold() { return this.slots.get(0).is(NtmItems.MOLD_INGOT.get()); }
    private boolean hasBladeMold() { return this.slots.get(0).is(NtmItems.MOLD_BLADE.get()); }
    public boolean hasMold() { return this.hasPlateMold() || this.hasIngotMold() || this.hasBladeMold(); }
    public int getCapacity() {
        if(this.hasIngotMold()) return CopperCastingRecipes.INGOT_QUANTA;
        if(this.hasPlateMold()) return CopperCastingRecipes.PLATE_QUANTA;
        if(this.hasBladeMold()) return CopperCastingRecipes.BLADE_QUANTA;
        return 0;
    }

    private boolean accepts(NTMMaterial material) {
        if(this.hasBladeMold()) return material == Mats.MAT_TUNGSTEN;
        if(this.hasIngotMold()) return material == Mats.MAT_DURA;
        return this.hasPlateMold() && CopperCastingRecipes.getPlateType(material) != null;
    }

    private static boolean accepts(ItemStack mold, NTMMaterial material) {
        if(mold.is(NtmItems.MOLD_BLADE.get())) return material == Mats.MAT_TUNGSTEN;
        if(mold.is(NtmItems.MOLD_INGOT.get())) return material == Mats.MAT_DURA;
        return mold.is(NtmItems.MOLD_PLATE_CAST.get()) && CopperCastingRecipes.getPlateType(material) != null;
    }

    private static int capacityFor(ItemStack mold, NTMMaterial material) {
        if(!accepts(mold, material)) return 0;
        if(mold.is(NtmItems.MOLD_BLADE.get())) return CopperCastingRecipes.BLADE_QUANTA;
        return mold.is(NtmItems.MOLD_INGOT.get())
                ? CopperCastingRecipes.INGOT_QUANTA
                : CopperCastingRecipes.PLATE_QUANTA;
    }

    /** Returns accepted quanta without mutating the caller's material stack. */
    public int pour(Mats.MaterialStack offered) {
        if(this.level == null || this.level.isClientSide || offered == null || offered.amount <= 0
                || !this.accepts(offered.material)
                || !this.slots.get(1).isEmpty()) return 0;
        if(this.amount > 0 && this.type != offered.material) return 0;
        int accepted = Math.min(offered.amount, Math.max(0, this.getCapacity() - this.amount));
        if(accepted > 0) {
            this.type = offered.material;
            this.amount += accepted;
            this.setChanged();
        }
        return accepted;
    }

    @Override
    public void updateEntity() {
        if(this.level == null || this.level.isClientSide) return;
        int oldCooloff = this.cooloff;
        if(this.accepts(this.type) && this.amount == this.getCapacity()
                && this.slots.get(1).isEmpty()) {
            if(--this.cooloff <= 0) {
                this.slots.set(1, this.hasIngotMold()
                        ? new ItemStack(NtmItems.INGOT_DURA_STEEL.get())
                        : this.hasBladeMold() ? new ItemStack(NtmItems.BLADE_TUNGSTEN.get())
                        : CopperCastingRecipes.getPlate(this.type));
                this.amount = 0;
                this.type = null;
                this.cooloff = 200;
                this.setChanged();
            }
        } else {
            this.cooloff = 200;
        }
        if(oldCooloff != this.cooloff) this.setChanged();
        this.networkPackNT(25);
    }

    public boolean insertMold(ItemStack stack) {
        if(!this.slots.get(0).isEmpty() || this.amount > 0
                || (!stack.is(NtmItems.MOLD_PLATE_CAST.get()) && !stack.is(NtmItems.MOLD_INGOT.get()) && !stack.is(NtmItems.MOLD_BLADE.get()))) return false;
        this.slots.set(0, stack.split(1));
        this.setChanged();
        return true;
    }

    public ItemStack takeMold() {
        if(this.amount > 0) return ItemStack.EMPTY;
        return this.removeItem(0, 1);
    }

    public ItemStack takeScraps() {
        ItemStack scraps = this.type != null ? CopperScrapsItem.create(new Mats.MaterialStack(this.type, this.amount)) : ItemStack.EMPTY;
        this.amount = 0;
        this.type = null;
        this.cooloff = 200;
        this.setChanged();
        return scraps;
    }

    /** Drop unknown or mold-incompatible material state; valid cast-plate saves remain supported. */
    private static NTMMaterial castableMaterial(int id, ItemStack mold) {
        NTMMaterial material = Mats.matById.get(id);
        return accepts(mold, material) ? material : null;
    }

    @Override public boolean canPlaceItem(int slot, ItemStack stack) { return false; }
    @Override public int[] getSlotsForFace(Direction direction) { return new int[] {1}; }
    @Override public boolean canTakeItemThroughFace(int index, ItemStack stack, Direction direction) { return index == 1; }
    @Override public AbstractContainerMenu createMenu(int id, Inventory inventory, Player player) { return null; }

    @Override protected void saveAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.saveAdditional(tag, registries);
        tag.putInt("amount", this.amount); tag.putInt("type", this.type == null ? -1 : this.type.id);
        tag.putInt("cooloff", this.cooloff);
    }
    @Override protected void loadAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.loadAdditional(tag, registries);
        this.type = castableMaterial(tag.getInt("type"), this.slots.get(0));
        this.amount = this.type == null ? 0 : Math.clamp(tag.getInt("amount"), 0, capacityFor(this.slots.get(0), this.type));
        this.cooloff = tag.contains("cooloff") ? Math.clamp(tag.getInt("cooloff"), 1, 200) : 200;
    }
    @Override public void serialize(RegistryFriendlyByteBuf buf) {
        super.serialize(buf);
        buf.writeInt(this.amount); buf.writeInt(this.cooloff); buf.writeInt(this.type == null ? -1 : this.type.id);
        ItemStack.OPTIONAL_STREAM_CODEC.encode(buf, this.slots.get(0));
        ItemStack.OPTIONAL_STREAM_CODEC.encode(buf, this.slots.get(1));
    }
    @Override public void deserialize(RegistryFriendlyByteBuf buf) {
        super.deserialize(buf);
        int amount = buf.readInt();
        this.cooloff = Math.clamp(buf.readInt(), 1, 200);
        int type = buf.readInt();
        this.slots.set(0, ItemStack.OPTIONAL_STREAM_CODEC.decode(buf));
        this.slots.set(1, ItemStack.OPTIONAL_STREAM_CODEC.decode(buf));
        this.type = castableMaterial(type, this.slots.get(0));
        this.amount = this.type == null ? 0 : Math.clamp(amount, 0, capacityFor(this.slots.get(0), this.type));
    }
}
