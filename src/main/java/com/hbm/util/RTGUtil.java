package com.hbm.util;

import com.hbm.config.NtmConfig;
import com.hbm.items.machine.RTGPelletItem;
import net.minecraft.core.NonNullList;
import net.minecraft.world.item.ItemStack;

// Port of the original com.hbm.util.RTGUtil (HBM's Nuclear Tech), with the two switches of the original VersatileConfig.rtgDecay()/scaleRTGPower()
// (:30-36). The common config need not be loaded while items register, so every caller reads them at run time; the original read them while
// registering the gold and lead pellets (ModItems.java:2655-2656) and the RT generator's heat limit, which gives the same values.
public class RTGUtil {

    /** Original VersatileConfig.rtgDecay(): MachineConfig 9.01_doRTGsDecay or 528 mode. */
    public static boolean rtgDecay() {
        return NtmConfig.enable528() || NtmConfig.COMMON.DO_RTGS_DECAY.get();
    }

    /** Original VersatileConfig.scaleRTGPower(): MachineConfig 9.00_scaleRTGPower or 528 mode. */
    public static boolean scaleRTGPower() {
        return NtmConfig.enable528() || NtmConfig.COMMON.SCALE_RTG_POWER.get();
    }

    public static int getPower(RTGPelletItem fuel, ItemStack stack) {
        return getPower(fuel, stack, scaleRTGPower());
    }

    public static int getPower(RTGPelletItem fuel, ItemStack stack, boolean scale) {
        return scale ? RTGPelletItem.getScaledPower(fuel, stack) : fuel.getHeat();
    }

    public static boolean hasHeat(NonNullList<ItemStack> inventory, int[] rtgSlots) {
        for(int slot : rtgSlots) {

            if(inventory.get(slot).isEmpty())
                continue;

            if(inventory.get(slot).getItem() instanceof RTGPelletItem)
                return true;
        }

        return false;
    }

    /** Original updateRTGs (:27-44): adds every pellet's power, then decays each pellet once and puts back what handleDecay returns. */
    public static int updateRTGs(NonNullList<ItemStack> inventory, int[] rtgSlots) {
        return updateRTGs(inventory, rtgSlots, rtgDecay(), scaleRTGPower());
    }

    /** {@link #updateRTGs(NonNullList, int[])} with both config switches passed in, so a GameTest covers either setting without changing the config. */
    public static int updateRTGs(NonNullList<ItemStack> inventory, int[] rtgSlots, boolean decay, boolean scale) {
        int newHeat = 0;
        for(int slot : rtgSlots) {

            ItemStack stack = inventory.get(slot);
            if(stack.isEmpty())
                continue;

            if(!(stack.getItem() instanceof RTGPelletItem pellet))
                continue;

            newHeat += getPower(pellet, stack, scale);
            inventory.set(slot, RTGPelletItem.handleDecay(stack, pellet, decay));
        }

        return newHeat;
    }

    /**
     * Gets the lifespan of an RTG based on half-life
     * @author UFFR
     * @param halfLife The half-life
     * @param type Half-life units: {@link HalfLifeType}
     * @param realYears Whether or not to use 365 days per year instead of 100 to calculate time
     * @return The half-life calculated into Minecraft ticks
     */
    public static long getLifespan(float halfLife, HalfLifeType type, boolean realYears) {
        // float arithmetic and the final cast as in the original (:54-69); the pellet constants depend on its rounding.
        float life = 0;
        switch(type) {
            case LONG:
                life = (48000 * (realYears ? 365 : 100) * 100) * halfLife;
                break;
            case MEDIUM:
                life = (48000 * (realYears ? 365 : 100)) * halfLife;
                break;
            case SHORT:
                life = 48000 * halfLife;
                break;
        }
        return (long) life;
    }

    /** Original com.hbm.interfaces.HalfLifeType. */
    public enum HalfLifeType {
        /** Counted in days **/
        SHORT,
        /** Counted in years **/
        MEDIUM,
        /** Counted in hundreds of years **/
        LONG
    }
}
