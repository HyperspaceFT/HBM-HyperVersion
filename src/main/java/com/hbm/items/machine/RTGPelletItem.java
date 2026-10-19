package com.hbm.items.machine;

import com.hbm.inventory.MetaHelper;
import com.hbm.items.NtmItems;
import com.hbm.items.machine.RTGPelletDepletedItem.DepletedRTGMaterial;
import com.hbm.util.RTGUtil;
import com.hbm.util.TagsUtil;
import net.minecraft.ChatFormatting;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.Tag;
import net.minecraft.network.chat.Component;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.util.Mth;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResultHolder;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.level.Level;

import java.text.NumberFormat;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.function.IntSupplier;

/**
 * Port of the original com.hbm.items.machine.ItemRTGPellet (HBM's Nuclear Tech). The remaining life is the long custom data value
 * PELLET_DEPLETION (the original NBT key). A stack without it counts as fresh (maximum life) and is not written to: the original wrote the
 * maximum into the stack the first time anything read it (:107-121), NEO only writes in {@link #decay}. The heat is a supplier because the
 * gold and lead pellets read doRTGsDecay, which NeoForge loads after registration.
 */
public class RTGPelletItem extends Item {

    public static final String KEY_DEPLETION = "PELLET_DEPLETION";
    /** The sixteen right-click facts of pellet_rtg (:40-57), as language keys desc.item.pellet_rtg.fact.1 to .16. */
    public static final int FACTS = 16;

    /** Original pelletList (:32): every pellet in construction order, which is the order the RT generator lists them. */
    public static final List<RTGPelletItem> PELLETS = new ArrayList<>();

    private final IntSupplier heat;
    private boolean doesDecay = false;
    private DepletedRTGMaterial decayMaterial = null;
    private long lifespan = 0;

    public RTGPelletItem(Properties properties, int heat) {
        this(properties, () -> heat);
    }

    public RTGPelletItem(Properties properties, IntSupplier heat) {
        super(properties.stacksTo(1));
        this.heat = heat;
        PELLETS.add(this);
    }

    /** Original setDecays (:59-64): the pellet turns into one pellet_rtg_depleted of this material when its life runs out. */
    public RTGPelletItem setDecays(DepletedRTGMaterial mat, long life) {
        doesDecay = true;
        decayMaterial = mat;
        lifespan = life;
        return this;
    }

    public long getMaxLifespan() {
        return lifespan;
    }

    public int getHeat() {
        return heat.getAsInt();
    }

    /** A new stack of the decay product, or an empty stack for a pellet that does not decay. */
    public ItemStack getDecayItem() {
        return decayMaterial == null ? ItemStack.EMPTY : MetaHelper.newStack(NtmItems.PELLET_RTG_DEPLETED.get(), 1, decayMaterial.ordinal());
    }

    public DepletedRTGMaterial getDecayMaterial() {
        return decayMaterial;
    }

    public boolean getDoesDecay() {
        return this.doesDecay;
    }

    public static ItemStack handleDecay(ItemStack stack, RTGPelletItem instance) {
        return handleDecay(stack, instance, RTGUtil.rtgDecay());
    }

    /** Original handleDecay (:83-92) with the config switch passed in: a spent pellet is replaced, any other one loses one tick of life. */
    public static ItemStack handleDecay(ItemStack stack, RTGPelletItem instance, boolean decay) {
        if(instance.getDoesDecay() && decay) {
            if(instance.getLifespan(stack) <= 0)
                return instance.getDecayItem();
            else
                instance.decay(stack);
        }

        return stack;
    }

    /** Original decay (:94-105). A stack without PELLET_DEPLETION starts from the maximum, as the original did after its first read. */
    public void decay(ItemStack stack) {
        if(stack.getItem() instanceof RTGPelletItem pellet) {
            if(!pellet.getDoesDecay())
                return;
            setLifespan(stack, getLifespan(stack) - 1);
        }
    }

    public long getLifespan(ItemStack stack) {
        if(stack.getItem() instanceof RTGPelletItem) {
            CompoundTag tag = TagsUtil.getCustomData(stack);
            return tag.contains(KEY_DEPLETION, Tag.TAG_ANY_NUMERIC) ? tag.getLong(KEY_DEPLETION) : getMaxLifespan();
        }
        return 0;
    }

    public static void setLifespan(ItemStack stack, long life) {
        CompoundTag tag = TagsUtil.getCustomData(stack);
        tag.putLong(KEY_DEPLETION, life);
        TagsUtil.putCustomData(stack, tag);
    }

    /** Original getScaledPower (:123-125): the heat times the remaining fraction of life, rounded up. */
    public static int getScaledPower(RTGPelletItem fuel, ItemStack stack) {
        return (short) Math.ceil(fuel.getHeat() * ((double) fuel.getLifespan(stack) / (double) fuel.getMaxLifespan()));
    }

    /** Original getDurabilityForDisplay (:143-147), used life over the maximum; HazardModifierRTGRadiation reads it. */
    public double getDepletion(ItemStack stack) {
        if(getMaxLifespan() <= 0) return 0D;
        return 1D - (double) getLifespan(stack) / (double) getMaxLifespan();
    }

    @Override
    public InteractionResultHolder<ItemStack> use(Level level, Player player, InteractionHand hand) {
        ItemStack stack = player.getItemInHand(hand);

        // Original onItemRightClick (:127-136): only the plutonium pellet, server side, a random fact in yellow and the orb sound.
        if(this == NtmItems.PELLET_RTG.get()) {
            if(!level.isClientSide) {
                player.sendSystemMessage(Component.translatable("desc.item.pellet_rtg.fact." + (level.random.nextInt(FACTS) + 1)).withStyle(ChatFormatting.YELLOW));
                level.playSound(null, player.getX(), player.getY(), player.getZ(), SoundEvents.EXPERIENCE_ORB_PICKUP, SoundSource.PLAYERS, 1.0F, 1.0F);
            }
            return InteractionResultHolder.consume(stack);
        }

        return super.use(level, player, hand);
    }

    // Original showDurabilityBar (:138-141).
    @Override
    public boolean isBarVisible(ItemStack stack) {
        return getDoesDecay() && getLifespan(stack) != getMaxLifespan();
    }

    // Drawn like ZirnoxRodItem: the remaining fraction, clamped, with the vanilla 1.21 hue.
    @Override
    public int getBarWidth(ItemStack stack) {
        return Math.round(13F - 13F * (float) Mth.clamp(getDepletion(stack), 0D, 1D));
    }

    @Override
    public int getBarColor(ItemStack stack) {
        return Mth.hsvToRgb(Math.max(0F, 1F - (float) Mth.clamp(getDepletion(stack), 0D, 1D)) / 3F, 1.0F, 1.0F);
    }

    // Original addInformation (:149-167). Its extended lines were hardcoded English under the advanced tooltip flag (F3+H), NEO uses keys.
    @Override
    public void appendHoverText(ItemStack stack, TooltipContext context, List<Component> tooltipComponents, TooltipFlag tooltipFlag) {
        tooltipComponents.add(Component.translatable(this.getDescriptionId() + ".desc").withStyle(ChatFormatting.GRAY));
        int power = getDoesDecay() && RTGUtil.scaleRTGPower() ? getScaledPower(this, stack) : getHeat();
        tooltipComponents.add(Component.translatable("desc.item.rtgHeat", power).withStyle(ChatFormatting.GRAY));
        if(getDoesDecay()) {
            long life = getLifespan(stack);
            tooltipComponents.add(Component.translatable("desc.item.rtgDecay", getDecayItem().getHoverName()).withStyle(ChatFormatting.GRAY));
            tooltipComponents.add(Component.literal(toPercentage(life, getMaxLifespan())).withStyle(ChatFormatting.GRAY));
            if(tooltipFlag.isAdvanced()) {
                String[] timeLeft = ticksToDate(life);
                String[] maxLife = ticksToDate(getMaxLifespan());
                tooltipComponents.add(Component.translatable("desc.item.rtgExtended").withStyle(ChatFormatting.GRAY));
                tooltipComponents.add(Component.translatable("desc.item.rtgTicks", String.valueOf(life), String.valueOf(getMaxLifespan())).withStyle(ChatFormatting.GRAY));
                tooltipComponents.add(Component.translatable("desc.item.rtgRemaining", (Object[]) timeLeft).withStyle(ChatFormatting.GRAY));
                tooltipComponents.add(Component.translatable("desc.item.rtgMaxLife", (Object[]) maxLife).withStyle(ChatFormatting.GRAY));
            }
        }
    }

    /** Original BobMathUtil.toPercentage (:135-137), float division; Locale.US instead of the JVM default for a stable format. */
    private static String toPercentage(float amount, float total) {
        return NumberFormat.getPercentInstance(Locale.US).format(amount / total);
    }

    /** Original BobMathUtil.ticksToDate (:139-153): years of 100 days of 48,000 ticks, and the rest of the day scaled to 0-10. */
    private static String[] ticksToDate(long ticks) {

        int tickDay = 48000;
        int tickYear = tickDay * 100;

        final String[] dateOut = new String[3];
        long year = Math.floorDiv(ticks, tickYear);
        byte day = (byte) Math.floorDiv(ticks - tickYear * year, tickDay);
        float time = ticks - (tickYear * year + tickDay * day);
        time = (float) convertScale(time, 0, tickDay, 0, 10F);
        dateOut[0] = String.valueOf(year);
        dateOut[1] = String.valueOf(day);
        dateOut[2] = String.valueOf(time);
        return dateOut;
    }

    /** Original BobMathUtil.convertScale (:164-168). */
    private static double convertScale(double toScale, double oldMin, double oldMax, double newMin, double newMax) {
        double prevRange = oldMax - oldMin;
        double newRange = newMax - newMin;
        return (((toScale - oldMin) * newRange) / prevRange) + newMin;
    }
}
