package com.hbm.blockentity.machine;

import api.hbm.tile.IHeatSource;
import com.hbm.blockentity.MachineBaseBlockEntity;
import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.blocks.DummyableBlock;
import com.hbm.inventory.material.MaterialShapes;
import com.hbm.inventory.material.Mats;
import com.hbm.inventory.menus.MachineCrucibleMenu;
import com.hbm.inventory.recipes.CopperCastingRecipes;
import com.hbm.items.CopperScrapsItem;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.HolderLookup;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.chat.Component;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.AbstractContainerMenu;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.ClipContext;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.HitResult;
import net.minecraft.world.phys.Vec3;
import net.minecraft.world.phys.shapes.CollisionContext;

/** Copper-only, unalloyed crucible route adapted from upstream TileEntityCrucible. */
public class MachineCrucibleBlockEntity extends MachineBaseBlockEntity {
    public static final int MAX_HEAT = 100_000;
    public static final int PROCESS_TIME = 20_000;
    public static final int CAPACITY = MaterialShapes.BLOCK.q(16);
    public int heat;
    public int progress;
    public int copper;

    public MachineCrucibleBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.MACHINE_CRUCIBLE.get(), pos, state, 9);
    }

    @Override protected Component getDefaultName() { return Component.translatable("container.machine_crucible"); }
    @Override public int getMaxStackSize() { return 1; }

    @Override
    public void updateEntity() {
        if(this.level == null || this.level.isClientSide) return;
        int oldHeat = this.heat, oldProgress = this.progress, oldCopper = this.copper;
        this.tryPullHeat();
        if(this.level.getGameTime() % 5 == 0) this.collectItems();

        int input = this.firstSmeltableSlot();
        if(this.heat >= MAX_HEAT / 2 && input >= 0) {
            int delta = (int) ((this.heat - MAX_HEAT / 2) * 0.05D);
            this.progress += delta;
            this.heat -= delta;
            if(this.progress >= PROCESS_TIME) {
                Mats.MaterialStack material = CopperCastingRecipes.getMaterial(this.slots.get(input));
                this.copper += material.amount;
                this.slots.get(input).shrink(1);
                this.progress = 0;
                this.setChanged();
            }
        } else {
            this.progress = 0;
        }
        this.tryPour();
        if(oldHeat != this.heat || oldProgress != this.progress || oldCopper != this.copper) this.setChanged();
        this.networkPackNT(25);
    }

    private void tryPullHeat() {
        if(this.heat >= MAX_HEAT) return;
        if(this.level.getBlockEntity(this.worldPosition.below()) instanceof IHeatSource source) {
            int difference = source.getHeatStored() - this.heat;
            if(difference == 0) return;
            // The crucible caps the difference before diffusion, unlike the combination oven.
            difference = Math.min(difference, MAX_HEAT - this.heat);
            if(difference > 0) {
                int received = (int) Math.ceil(difference * 0.25D);
                source.useUpHeat(received);
                this.heat += received;
                return;
            }
        }
        this.heat = Math.max(0, this.heat - Math.max(this.heat / 1000, 1));
    }

    public boolean isItemSmeltable(ItemStack stack) {
        Mats.MaterialStack material = CopperCastingRecipes.getMaterial(stack);
        return material != null && material.amount <= CAPACITY - this.copper;
    }

    private int firstSmeltableSlot() {
        for(int i = 0; i < this.slots.size(); i++) if(this.isItemSmeltable(this.slots.get(i))) return i;
        return -1;
    }

    private void collectItems() {
        AABB intake = new AABB(this.worldPosition.getX() - 0.5D, this.worldPosition.getY() + 0.5D,
                this.worldPosition.getZ() - 0.5D, this.worldPosition.getX() + 1.5D,
                this.worldPosition.getY() + 1D, this.worldPosition.getZ() + 1.5D);
        for(ItemEntity entity : this.level.getEntitiesOfClass(ItemEntity.class, intake)) {
            if(!entity.isAlive() || !this.isItemSmeltable(entity.getItem())) continue;
            for(int i = 0; i < this.slots.size() && !entity.getItem().isEmpty(); i++) {
                if(!this.slots.get(i).isEmpty()) continue;
                this.slots.set(i, entity.getItem().split(1));
                this.setChanged();
            }
            if(entity.getItem().isEmpty()) entity.discard();
        }
    }

    public Direction getPourDirection() {
        // Without an alloy recipe, the original sends pure metal to the rear waste spout.
        return this.getBlockState().getValue(DummyableBlock.FACING).getOpposite();
    }

    private void tryPour() {
        if(this.copper <= 0) return;
        Direction direction = this.getPourDirection();
        Vec3 start = new Vec3(this.worldPosition.getX() + 0.5D + direction.getStepX() * 1.875D,
                this.worldPosition.getY() + 0.25D,
                this.worldPosition.getZ() + 0.5D + direction.getStepZ() * 1.875D);
        // A blocked, absent or full receiver keeps the material in the crucible (upstream safe pour).
        BlockHitResult hit = this.level.clip(new ClipContext(start, start.add(0, -6, 0),
                ClipContext.Block.COLLIDER, ClipContext.Fluid.ANY, CollisionContext.empty()));
        if(hit.getType() != HitResult.Type.BLOCK || hit.getDirection() != Direction.UP) return;
        if(this.level.getBlockEntity(hit.getBlockPos()) instanceof FoundryMoldBlockEntity mold) {
            int offered = Math.min(this.copper, CopperCastingRecipes.POUR_QUANTA);
            this.copper -= mold.pour(new Mats.MaterialStack(Mats.MAT_COPPER, offered));
        }
    }

    public ItemStack takeScraps() {
        ItemStack scraps = CopperScrapsItem.create(this.copper);
        this.copper = 0;
        this.setChanged();
        return scraps;
    }

    @Override public boolean canPlaceItem(int slot, ItemStack stack) {
        // Vanilla hopper merges can grow the live stack without consulting the container limit.
        return slot >= 0 && slot < this.slots.size() && this.slots.get(slot).isEmpty() && this.isItemSmeltable(stack);
    }
    @Override public int[] getSlotsForFace(Direction direction) { return new int[] {0, 1, 2, 3, 4, 5, 6, 7, 8}; }
    @Override public boolean canTakeItemThroughFace(int index, ItemStack stack, Direction direction) { return false; }

    @Override
    protected void saveAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.saveAdditional(tag, registries);
        tag.putInt("heat", this.heat);
        tag.putInt("progress", this.progress);
        tag.putInt("copper", this.copper);
    }

    @Override
    protected void loadAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.loadAdditional(tag, registries);
        this.heat = Math.clamp(tag.getInt("heat"), 0, MAX_HEAT);
        this.progress = Math.clamp(tag.getInt("progress"), 0, PROCESS_TIME - 1);
        this.copper = Math.clamp(tag.getInt("copper"), 0, CAPACITY);
    }

    @Override public void serialize(RegistryFriendlyByteBuf buf) {
        super.serialize(buf);
        buf.writeInt(this.heat); buf.writeInt(this.progress); buf.writeInt(this.copper);
    }
    @Override public void deserialize(RegistryFriendlyByteBuf buf) {
        super.deserialize(buf);
        this.heat = buf.readInt(); this.progress = buf.readInt(); this.copper = buf.readInt();
    }
    @Override public AbstractContainerMenu createMenu(int id, Inventory inventory, Player player) {
        return new MachineCrucibleMenu(id, inventory, this);
    }
}
