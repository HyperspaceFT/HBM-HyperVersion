package com.hbm.items.special;

import com.hbm.blocks.ITooltipProvider;
import com.hbm.items.NtmItems;
import com.hbm.lib.ModEffect;
import com.hbm.registry.NtmSoundEvents;
import net.minecraft.ChatFormatting;
import net.minecraft.core.Holder;
import net.minecraft.network.chat.Component;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResultHolder;
import net.minecraft.world.effect.MobEffect;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.level.Level;
import net.neoforged.neoforge.common.util.FakePlayer;

import javax.annotation.Nullable;
import java.util.List;
import java.util.function.BiConsumer;

/**
 * Original ItemSimpleConsumable (ItemSimpleConsumable.java:25-95): right click runs a server action on the stack, no use duration.
 * Only the use action is ported, for radaway, iv_empty and iv_blood; the hit actions and the other consumables built on it
 * (the syringes, the stronger radaway variants, iv_xp, ...) are deferred.
 */
public class SimpleConsumableItem extends Item {

    @Nullable
    private BiConsumer<ItemStack, Player> useActionServer;

    public SimpleConsumableItem(Properties properties) {
        super(properties);
    }

    // ItemSimpleConsumable.java:93 setUseActionServer
    public SimpleConsumableItem setUseActionServer(BiConsumer<ItemStack, Player> delegate) {
        this.useActionServer = delegate;
        return this;
    }

    // ItemSimpleConsumable.java:37-47. sidedSuccess instead of returning the stack unchanged: the vanilla result type that consumes the
    // click without a use duration; the client only gains the arm swing (NEO-only cosmetic), it changes no state.
    @Override
    public InteractionResultHolder<ItemStack> use(Level level, Player player, InteractionHand hand) {
        ItemStack stack = player.getItemInHand(hand);

        if(!level.isClientSide && this.useActionServer != null) {
            this.useActionServer.accept(stack, player);
            // The action may have emptied the stack and put the container into that very slot (Inventory.add takes the first slot
            // that isEmpty()). Returning the old, empty stack would make ServerPlayerGameMode clear the hand and delete the
            // container, so hand back whatever the hand holds now.
            stack = player.getItemInHand(hand);
        }

        return InteractionResultHolder.sidedSuccess(stack, level.isClientSide());
    }

    // ItemSimpleConsumable.java:61-65. The original's stackSize-- is "consume unless creative": 1.7.10 ItemInWorldManager.tryUseItem
    // restored the stack size of a creative player. The container is still given in creative (original).
    public static void giveSoundAndDecrement(ItemStack stack, LivingEntity entity, SoundEvent sound, ItemStack container) {
        stack.consume(1, entity);
        entity.level().playSound(null, entity.getX(), entity.getY(), entity.getZ(), sound, SoundSource.PLAYERS, 1F, 1F);
        tryAddItem(entity, container);
    }

    // ItemSimpleConsumable.java:67-75: an active effect keeps its remaining duration on top of the new one
    public static void addPotionEffect(LivingEntity entity, Holder<MobEffect> effect, int duration, int level) {
        MobEffectInstance active = entity.getEffect(effect);

        if(active == null) {
            entity.addEffect(new MobEffectInstance(effect, duration, level));
        } else {
            entity.addEffect(new MobEffectInstance(effect, active.getDuration() + duration, level));
        }
    }

    // ItemSimpleConsumable.java:77-84
    public static void tryAddItem(LivingEntity entity, ItemStack stack) {
        if(entity instanceof Player player) {
            if(!player.getInventory().add(stack)) player.drop(stack, false);
        }
    }

    // ItemSimpleConsumable.java:86-89
    public static void doRadaway(ItemStack stack, Player user, int duration) {
        giveSoundAndDecrement(stack, user, NtmSoundEvents.RADAWAY.get(), new ItemStack(NtmItems.IV_EMPTY.get()));
        addPotionEffect(user, ModEffect.RADAWAY, duration, 0);
    }

    // EntityDamageUtil.java:509-511: a player that is not a FakePlayer
    private static boolean isRealPlayer(Entity entity) {
        return entity instanceof Player && !(entity instanceof FakePlayer);
    }

    // ItemSimpleConsumable.java:139-141
    public static void radaway(ItemStack stack, Player user) {
        doRadaway(stack, user, 140);
    }

    // ItemSimpleConsumable.java:113-118
    public static void ivEmpty(ItemStack stack, Player user) {
        if(!isRealPlayer(user)) return;

        giveSoundAndDecrement(stack, user, NtmSoundEvents.SYRINGE.get(), new ItemStack(NtmItems.IV_BLOOD.get()));
        user.setHealth(Math.max(user.getHealth() - 5F, 0F));
        // The original calls onDeath(DamageSource.magic) directly, bypassing armor, totems and invulnerability; die() is the 1.21 counterpart.
        if(user.getHealth() <= 0) user.die(user.damageSources().magic());
    }

    // ItemSimpleConsumable.java:120-123
    public static void ivBlood(ItemStack stack, Player user) {
        giveSoundAndDecrement(stack, user, NtmSoundEvents.RADAWAY.get(), new ItemStack(NtmItems.IV_EMPTY.get()));
        user.heal(5F);
    }

    // ItemCustomLore.java:26-52: the '$'-split <name>.desc lines, only when the key exists
    @Override
    public void appendHoverText(ItemStack stack, TooltipContext context, List<Component> components, TooltipFlag flag) {
        String[] lines = ITooltipProvider.getDescriptionOrNull(stack);
        if(lines != null) for(String s : lines) components.add(Component.translatable(s).withStyle(ChatFormatting.GRAY));
    }
}
