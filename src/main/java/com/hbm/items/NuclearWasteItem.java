package com.hbm.items;

import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;

import javax.annotation.Nullable;

/** Nuclear waste that never despawns and survives attacks when dropped (original ItemNuclearWaste.java:12-34). */
public class NuclearWasteItem extends Item {

    public NuclearWasteItem(Properties properties) {
        super(properties);
    }

    @Override
    public boolean hasCustomEntity(ItemStack stack) {
        return true;
    }

    // Original getEntityLifespan (ItemNuclearWaste.java:17-20): ItemEntity reads this in its constructor, so the age keeps ticking
    // (bobbing and ground merging stay vanilla) but the item never reaches its despawn age.
    @Override
    public int getEntityLifespan(ItemStack itemStack, Level level) {
        return Integer.MAX_VALUE;
    }

    /**
     * The original replaced the dropped item with EntityItemWaste (invulnerable and ignoring every attack, EntityItemWaste.java:22-30;
     * pickup delay 10). NEO keeps the vanilla entity and adjusts it in place: NeoForge only swaps entities whose class is exactly
     * ItemEntity, so returning another ItemEntity would run this hook again for the replacement forever. Returning null keeps the
     * original entity. Damage that bypasses invulnerability (the void, /kill) still removes it.
     */
    @Override
    public @Nullable Entity createEntity(Level level, Entity location, ItemStack stack) {
        if(location instanceof ItemEntity item) {
            item.setInvulnerable(true);
            item.setPickUpDelay(10);
        }
        return null;
    }
}
