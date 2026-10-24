package com.hbm.items.tools;

import api.hbm.item.IGasMask;
import com.hbm.handler.ArmorModHandler;
import com.hbm.items.armor.ItemArmorMod;
import com.hbm.registry.NtmSoundEvents;
import com.hbm.util.ArmorUtil;
import com.hbm.util.TagsUtil;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResultHolder;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;

/**
 * Original ItemFilter: right click screws the filter into the worn gas mask and hands back the previous filter.
 */
public class GasMaskFilterItem extends Item {

    public GasMaskFilterItem(Properties properties) {
        super(properties);
    }

    // Original ItemFilter.java:22-72. Only the server changes the mask, the hand and plays the sound; the client
    // makes the same decision without touching anything so both sides agree on the result.
    @Override
    public InteractionResultHolder<ItemStack> use(Level level, Player player, InteractionHand hand) {

        ItemStack stack = player.getItemInHand(hand);
        ItemStack helmet = player.getItemBySlot(EquipmentSlot.HEAD);

        if(helmet.isEmpty()) return InteractionResultHolder.pass(stack);

        if(!(helmet.getItem() instanceof IGasMask) && ArmorModHandler.hasMods(helmet)) {

            // pryMods drops unreadable mod slots from the helmet, so the client only peeks
            ItemStack mask = level.isClientSide() ? peekHelmetMod(level, helmet) : ArmorModHandler.pryMods(level, helmet)[ArmorModHandler.HELMET_ONLY];

            if(!mask.isEmpty()) {
                // No IGasMask armor mod exists in NEO yet, so this branch cannot install anything for now; it is ported for
                // the attachable masks. applyMod casts to ItemArmorMod, hence the guard.
                ItemStack ret = installFilterOn(mask, stack, level, player);

                if(!level.isClientSide() && mask.getItem() instanceof ItemArmorMod) {
                    ArmorModHandler.applyMod(level, helmet, mask);
                }

                return result(ret, stack, level);
            }
        }

        return result(installFilterOn(helmet, stack, level, player), stack, level);
    }

    /**
     * @return the stack the hand ends up with (the previous filter or EMPTY), or null when nothing is installed
     */
    private ItemStack installFilterOn(ItemStack helmet, ItemStack filter, Level level, Player player) {

        if(!(helmet.getItem() instanceof IGasMask mask)) return null;
        if(!mask.isFilterApplicable(helmet, player, filter)) return null;
        if(level.isClientSide()) return filter;

        ItemStack copy = filter.copy();
        ItemStack current = ArmorUtil.getGasMaskFilter(level, helmet);

        ArmorUtil.installGasMaskFilter(level, helmet, copy);

        level.playSound(null, player.getX(), player.getY(), player.getZ(), NtmSoundEvents.GASMASK_SCREW.get(), SoundSource.PLAYERS, 1F, 1F);

        if(!current.isEmpty()) return current;

        // 1.7.10 ItemInWorldManager.tryUseItem restored the count in creative, so the filter stayed in hand;
        // 1.21 ServerPlayerGameMode.useItem has no such restore for use()
        return player.hasInfiniteMaterials() ? filter : ItemStack.EMPTY;
    }

    private static InteractionResultHolder<ItemStack> result(ItemStack ret, ItemStack stack, Level level) {
        if(ret == null) return InteractionResultHolder.pass(stack);
        return InteractionResultHolder.sidedSuccess(level.isClientSide() ? stack : ret, level.isClientSide());
    }

    // Read-only counterpart of ArmorModHandler.pryMods(level, helmet)[HELMET_ONLY]
    private static ItemStack peekHelmetMod(Level level, ItemStack helmet) {
        CompoundTag mods = TagsUtil.getCustomData(helmet).getCompound(ArmorModHandler.MOD_COMPOUND_KEY);
        CompoundTag cmp = mods.getCompound(ArmorModHandler.MOD_SLOT_KEY + ArmorModHandler.HELMET_ONLY);

        if(cmp.isEmpty()) return ItemStack.EMPTY;

        return ItemStack.parse(level.registryAccess(), cmp).orElse(ItemStack.EMPTY);
    }
}
