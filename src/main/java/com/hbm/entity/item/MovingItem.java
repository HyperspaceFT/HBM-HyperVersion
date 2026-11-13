package com.hbm.entity.item;

import api.hbm.conveyor.IConveyorItem;
import api.hbm.conveyor.IEnterableBlock;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.Tag;
import net.minecraft.network.syncher.EntityDataAccessor;
import net.minecraft.network.syncher.EntityDataSerializers;
import net.minecraft.network.syncher.SynchedEntityData;
import net.minecraft.network.syncher.SynchedEntityData.Builder;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;

import javax.annotation.Nullable;

/** Original EntityMovingItem: one item stack riding a conveyor belt. */
public class MovingItem extends MovingConveyorObject implements IConveyorItem {

    private static final EntityDataAccessor<ItemStack> ITEM = SynchedEntityData.defineId(MovingItem.class, EntityDataSerializers.ITEM_STACK);

    public MovingItem(EntityType<? extends MovingItem> entityType, Level level) {
        super(entityType, level);
    }

    /** Writes the stack into the synced data; changing the stack {@link #getItemStack()} returns does not reach clients. */
    public void setItemStack(ItemStack stack) {
        this.entityData.set(ITEM, stack);
    }

    /** A copy of the carried stack. */
    @Override
    public ItemStack getItemStack() {
        return this.entityData.get(ITEM).copy();
    }

    /** Adds the item to the player's inventory; what does not fit stays on the belt */
    @Override
    public InteractionResult interact(Player player, InteractionHand hand) {

        if(!this.level.isClientSide && !this.isRemoved()) {
            // Inventory.add returns false when only part of the stack fits, so the result is read from the stack it shrinks
            ItemStack give = this.getItemStack();
            int before = give.getCount();
            player.getInventory().add(give);

            if(give.isEmpty()) {
                this.discard();
            } else if(give.getCount() < before) {
                this.setItemStack(give);
            }
        }

        return InteractionResult.PASS;
    }

    /** A player's attack knocks the item off the belt (EntityMovingItem.java:50-57). */
    @Override
    public boolean skipAttackInteraction(Entity attacker) {
        this.knockOff();
        return true;
    }

    /** Ensures the item is knocked off the belt due to non-player attacks (explosions, etc) */
    @Override
    public boolean hurt(DamageSource source, float amount) {
        this.knockOff();
        return true;
    }

    private void knockOff() {
        if(!this.level.isClientSide && !this.isRemoved()) {
            this.discard();
            this.level.addFreshEntity(new ItemEntity(this.level, this.getX(), this.getY(), this.getZ(), this.getItemStack()));
        }
    }

    @Override
    public void enterBlock(IEnterableBlock enterable, BlockPos pos, @Nullable Direction dir) {
        if(this.isRemoved()) return;

        if(enterable.canItemEnter(this.level, pos, dir, this)) {
            enterable.onItemEnter(this.level, pos, dir, this);
            this.discard();
        }
    }

    /** EntityMovingItem.java:118-133: dropped two movement steps ahead with twice the belt speed, despawning after 60 seconds. */
    @Override
    public boolean onLeaveConveyor() {

        if(this.isRemoved()) return true;

        this.discard();
        ItemEntity item = new ItemEntity(
                this.level,
                this.position().x + this.getDeltaMovement().x * 2,
                this.position().y + this.getDeltaMovement().y * 2,
                this.position().z + this.getDeltaMovement().z * 2,
                this.getItemStack()
        );
        item.lifespan = 60 * 20;
        item.setDeltaMovement(this.getDeltaMovement().x * 2, 0.1, this.getDeltaMovement().z * 2);
        item.hasImpulse = true;
        this.level.addFreshEntity(item);

        return true;
    }

    @Override
    protected void defineSynchedData(Builder builder) {
        builder.define(ITEM, ItemStack.EMPTY);
    }

    @Override
    protected void readAdditionalSaveData(CompoundTag tag) {
        ItemStack stack = tag.contains("Item", Tag.TAG_COMPOUND) ? ItemStack.parseOptional(this.registryAccess(), tag.getCompound("Item")) : ItemStack.EMPTY;

        this.setItemStack(stack);

        if(stack.isEmpty()) this.discard();
    }

    @Override
    protected void addAdditionalSaveData(CompoundTag tag) {
        ItemStack stack = this.entityData.get(ITEM);

        if(!stack.isEmpty()) tag.put("Item", stack.save(this.registryAccess()));
    }
}
