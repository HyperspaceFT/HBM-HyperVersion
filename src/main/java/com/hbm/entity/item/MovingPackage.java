package com.hbm.entity.item;

import api.hbm.conveyor.IConveyorPackage;
import api.hbm.conveyor.IEnterableBlock;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.Tag;
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
import java.util.Arrays;

/**
 * Original EntityMovingPackage: several item stacks boxed up on a conveyor belt. The contents are not synced to clients (the
 * original has no watched data, :27-28); the renderer draws the same crate for every package. Every way out (entering a block,
 * a right click, damage, leaving the belt) first checks that the package still exists, so the contents are handed out once; a
 * right click, damage and leaving the belt remove the package before handing out, entering a block removes it once the block
 * has taken the contents (as the original, :79-81).
 */
public class MovingPackage extends MovingConveyorObject implements IConveyorPackage {

    /** Never null and without null elements; empty slots after loading are empty stacks. */
    protected ItemStack[] contents = new ItemStack[0];

    public MovingPackage(EntityType<? extends MovingPackage> entityType, Level level) {
        super(entityType, level);
    }

    /** Original :30-32: copies every stack. */
    public void setItemStacks(ItemStack[] stacks) {
        this.contents = new ItemStack[stacks.length];
        for(int i = 0; i < stacks.length; i++) this.contents[i] = stacks[i] == null ? ItemStack.EMPTY : stacks[i].copy();
    }

    @Override
    public ItemStack[] getItemStacks() {
        return this.contents;
    }

    /**
     * Original :39-54: every stack goes to the player, what does not fit is dropped 0.125 above the package. The original drops the
     * whole stack whenever the inventory does not take all of it (addItemStackToInventory, like 1.21's Inventory.add, answers false
     * after a partial fit), which duplicates the part that went in; NEO drops only the rest (GOAL31 decision 4).
     */
    @Override
    public InteractionResult interact(Player player, InteractionHand hand) {

        if(!this.level.isClientSide && !this.isRemoved()) {
            this.discard();

            for(ItemStack stack : this.contents) {
                if(stack.isEmpty()) continue;

                ItemStack give = stack.copy();
                player.getInventory().add(give);

                if(!give.isEmpty()) {
                    this.level.addFreshEntity(new ItemEntity(this.level, this.getX(), this.getY() + 0.125, this.getZ(), give));
                }
            }
        }

        return InteractionResult.PASS;
    }

    /** Original :56-67: a player's attack breaks the package. */
    @Override
    public boolean skipAttackInteraction(Entity attacker) {
        this.breakOpen();
        return true;
    }

    /** Original :69-73: any other damage breaks it too. */
    @Override
    public boolean hurt(DamageSource source, float amount) {
        this.breakOpen();
        return true;
    }

    private void breakOpen() {
        if(!this.level.isClientSide && !this.isRemoved()) {
            this.discard();

            for(ItemStack stack : this.contents) {
                if(!stack.isEmpty()) this.level.addFreshEntity(new ItemEntity(this.level, this.getX(), this.getY() + 0.125, this.getZ(), stack.copy()));
            }
        }
    }

    /** Original :75-83. */
    @Override
    public void enterBlock(IEnterableBlock enterable, BlockPos pos, @Nullable Direction dir) {
        if(this.isRemoved()) return;

        if(enterable.canPackageEnter(this.level, pos, dir, this)) {
            enterable.onPackageEnter(this.level, pos, dir, this);
            this.discard();
        }
    }

    /**
     * Original :85-100: every stack is dropped two movement steps ahead with twice the belt speed, without the moving item's short
     * despawn time. Unlike the original, a package that is already gone (cleared by the cram check) drops nothing, as the moving
     * item (EntityMovingItem.java:121).
     */
    @Override
    public boolean onLeaveConveyor() {

        if(this.isRemoved()) return true;

        this.discard();

        for(ItemStack stack : this.contents) {
            if(stack.isEmpty()) continue;

            ItemEntity item = new ItemEntity(
                    this.level,
                    this.position().x + this.getDeltaMovement().x * 2,
                    this.position().y + this.getDeltaMovement().y * 2,
                    this.position().z + this.getDeltaMovement().z * 2,
                    stack.copy()
            );
            item.setDeltaMovement(this.getDeltaMovement().x * 2, 0.1, this.getDeltaMovement().z * 2);
            item.hasImpulse = true;
            this.level.addFreshEntity(item);
        }

        return true;
    }

    @Override
    protected void defineSynchedData(Builder builder) { }

    /** Original :119-132. A package that loads without contents stays (unlike the moving item); missing slots are empty stacks. */
    @Override
    protected void readAdditionalSaveData(CompoundTag tag) {
        this.contents = new ItemStack[Math.max(0, tag.getInt("count"))];
        Arrays.fill(this.contents, ItemStack.EMPTY);
        ListTag list = tag.getList("contents", Tag.TAG_COMPOUND);

        for(int i = 0; i < list.size(); i++) {
            CompoundTag entry = list.getCompound(i);
            int slot = entry.getByte("slot") & 255;

            if(slot < this.contents.length) {
                this.contents[slot] = ItemStack.parseOptional(this.registryAccess(), entry);
            }
        }
    }

    /** Original :102-117: the filled slots with their byte "slot", and the array length as "count". */
    @Override
    protected void addAdditionalSaveData(CompoundTag tag) {
        ListTag list = new ListTag();

        for(int i = 0; i < this.contents.length; i++) {
            if(!this.contents[i].isEmpty()) {
                CompoundTag entry = new CompoundTag();
                entry.putByte("slot", (byte) i);
                list.add(this.contents[i].save(this.registryAccess(), entry));
            }
        }

        tag.put("contents", list);
        tag.putInt("count", this.contents.length);
    }
}
