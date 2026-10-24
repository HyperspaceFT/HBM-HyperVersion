package com.hbm.items.food;

import com.hbm.blocks.ITooltipProvider;
import com.hbm.config.NtmConfig;
import com.hbm.extprop.HbmLivingAttachments;
import com.hbm.lib.ModEffect;
import net.minecraft.ChatFormatting;
import net.minecraft.network.chat.Component;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResultHolder;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.food.FoodProperties;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.level.Level;

import javax.annotation.Nullable;
import java.util.List;
import java.util.function.Consumer;

/**
 * Original ItemPill (ItemPill.java, an always edible ItemFood with 0 hunger), reduced to the two pills of Goal 26D: radx and siox.
 * The other pills (iodine, plan_c, pill_red, pill_herbal, xanax, chocolate, fmn, five_htp) are NOT ported.
 * The effect that follows potion sickness is chosen per item through the constructor.
 */
public class PillItem extends Item {

    // ItemPill.java:23-26 ItemFood(0, false) + setAlwaysEdible; getUseDuration below keeps the original's 10 ticks
    private static final FoodProperties PILL = new FoodProperties.Builder().nutrition(0).saturationModifier(0F).alwaysEdible().build();

    // ItemPill.java:57-59
    public static final Consumer<LivingEntity> LAMBDA_RADX = (eater) -> {
        eater.addEffect(new MobEffectInstance(ModEffect.RADX, 3 * 60 * 20, 0));
    };
    // ItemPill.java:61-64
    public static final Consumer<LivingEntity> LAMBDA_SIOX = (eater) -> {
        HbmLivingAttachments.setAsbestos(eater, 0);
        HbmLivingAttachments.setBlackLung(eater, Math.min(HbmLivingAttachments.getBlackLung(eater), HbmLivingAttachments.maxBlacklung / 5));
    };

    @Nullable
    private final Consumer<LivingEntity> finishUsingItem;

    public PillItem(Properties properties, @Nullable Consumer<LivingEntity> finishUsingItem) {
        super(properties.food(PILL));
        this.finishUsingItem = finishUsingItem;
    }

    // ItemPill.java:30-34, server only: potion sickness first (5 seconds), then the pill's own effect
    @Override
    public ItemStack finishUsingItem(ItemStack stack, Level level, LivingEntity eater) {
        // vanilla eating: consumes one unless the player has infinite materials, plays the eating sound, advancements and stats
        ItemStack result = super.finishUsingItem(stack, level, eater);

        if(!level.isClientSide) {
            NtmConfig.applyPotionSickness(eater, 5);
            if(this.finishUsingItem != null) this.finishUsingItem.accept(eater);
        }

        return result;
    }

    // ItemPill.java:123-125
    @Override public int getUseDuration(ItemStack stack, LivingEntity entity) { return 10; }

    // ItemPill.java:127-134: the original never starts using while the player has potion sickness; pass lets the other hand act
    @Override
    public InteractionResultHolder<ItemStack> use(Level level, Player player, InteractionHand hand) {
        if(NtmConfig.hasPotionSickness(player)) return InteractionResultHolder.pass(player.getItemInHand(hand));

        // always edible, so the vanilla food path starts using it
        return super.use(level, player, hand);
    }

    // ItemPill.java:108-120: the '$'-split <name>.desc lines, only when the key exists
    @Override
    public void appendHoverText(ItemStack stack, TooltipContext context, List<Component> components, TooltipFlag flag) {
        String[] lines = ITooltipProvider.getDescriptionOrNull(stack);
        if(lines != null) for(String s : lines) components.add(Component.translatable(s).withStyle(ChatFormatting.GRAY));
    }
}
