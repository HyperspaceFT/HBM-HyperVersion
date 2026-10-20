package com.hbm.blockentity.machine.rbmk;

import com.hbm.config.NtmConfig;

/**
 * Original RBMKDials: the RBMK dials were per-world game rules there (RBMKDials.java:17-51); NEO keeps them in the common
 * config section "rbmk" (CommonConfig), read at call time, so the server's values apply. The getters keep the original names
 * and clamps but take no World. dialSaveDials does not apply and the ReaSim dials are deferred with ReaSim.
 */
public class RBMKDials {

    /**
     * Returns the amount of heat per tick removed from components passively, when at an edge
     * @return >0
     */
    public static double getPassiveCooling() {
        return NtmConfig.COMMON.DIAL_PASSIVE_COOLING.get();
    }

    /**
     * Returns the amount of heat per tick removed from components passively, when surrounded by other components
     * @return >0
     */
    public static double getPassiveCoolingInner() {
        return NtmConfig.COMMON.DIAL_PASSIVE_COOLING_INNER.get();
    }

    /**
     * Returns the percentual step size how quickly neighboring component heat equalizes. 1 is instant, 0.5 is in 50% steps, et cetera.
     * @return [0;1]
     */
    public static double getColumnHeatFlow() {
        return NtmConfig.COMMON.DIAL_COLUMN_HEAT_FLOW.get();
    }

    /**
     * Returns a modifier for fuel rod diffusion, i.e. how quickly the core and hull temperatures equalize.
     * @return >0
     */
    public static double getFuelDiffusionMod() {
        return NtmConfig.COMMON.DIAL_DIFFUSION_MOD.get();
    }

    /**
     * Returns the percentual step size how quickly the fuel hull heat and the component heat equalizes. 1 is instant, 0.5 is in 50% steps, et cetera.
     * @return [0;1]
     */
    public static double getFuelHeatProvision() {
        return NtmConfig.COMMON.DIAL_HEAT_PROVISION.get();
    }

    /**
     * Simple integer that decides how tall the structure is. As in the original (RBMKDials.java:96), the configured height
     * (2 to 16, default 4) minus one, i.e. the number of blocks above the core.
     * Changing the config does not resize columns that are already placed; the original does not either.
     * @return [1;15]
     */
    public static int getColumnHeight() {
        return NtmConfig.COMMON.DIAL_COLUMN_HEIGHT.get() - 1;
    }

    /**
     * Whether or not scrap entities despawn on their own or remain alive until picked up.
     */
    public static boolean getPermaScrap() {
        return NtmConfig.COMMON.DIAL_ENABLE_PERMA_SCRAP.get();
    }

    /**
     * How many heat units are consumed per mB water used.
     * @return >0
     */
    public static double getBoilerHeatConsumption() {
        return NtmConfig.COMMON.DIAL_BOILER_HEAT_CONSUMPTION.get();
    }

    /**
     * A multiplier for how quickly the control rods move.
     * @return >0
     */
    public static double getControlSpeed() {
        return NtmConfig.COMMON.DIAL_CONTROL_SPEED.get();
    }

    /**
     * A multiplier for how much flux the rods give out.
     * @return >0
     */
    public static double getReactivityMod() {
        return NtmConfig.COMMON.DIAL_REACTIVITY_MOD.get();
    }

    /**
     * A multiplier for how much flux the rods give out.
     * @return >0
     */
    public static double getOutgasserMod() {
        return NtmConfig.COMMON.DIAL_OUTGASSER_SPEED_MOD.get();
    }

    /**
     * A multiplier for how high the power surge goes when inserting control rods.
     * The original's client branch read the passive cooling dial instead (RBMKDials.java:262-264); NEO reads the config on both sides.
     * @return >0
     */
    public static double getSurgeMod() {
        return NtmConfig.COMMON.DIAL_CONTROL_SURGE_MOD.get();
    }

    /**
     * Simple integer that decides how far the flux of a normal fuel rod reaches.
     * @return [1;100]
     */
    public static int getFluxRange() {
        return NtmConfig.COMMON.DIAL_FLUX_RANGE.get();
    }

    /**
     * Whether or not fuel columns should initiate a meltdown when overheating
     * The method is in reverse because the default for older worlds will be 'false'
     */
    public static boolean getMeltdownsDisabled() {
        return NtmConfig.COMMON.DIAL_DISABLE_MELTDOWNS.get();
    }

    /**
     * Whether or not connected pipes and turbines should explode when the reactor undergoes a meltdown.
     */
    public static boolean getOverpressure() {
        return NtmConfig.COMMON.DIAL_ENABLE_MELTDOWN_OVERPRESSURE.get();
    }

    /**
     * The percentage of neutrons to moderate from fast to slow when they pass through a moderator.
     */
    public static double getModeratorEfficiency() {
        return NtmConfig.COMMON.DIAL_MODERATOR_EFFICIENCY.get();
    }

    /**
     * The percentage of neutrons to be absorbed when a stream hits an absorber column.
     */
    public static double getAbsorberEfficiency() {
        return NtmConfig.COMMON.DIAL_ABSORBER_EFFICIENCY.get();
    }

    /**
     * How many °C are generated per one flux that hits an absorber.
     */
    public static double getAbsorberHeatConversion() {
        return NtmConfig.COMMON.DIAL_ABSORBER_HEAT_CONVERSION.get();
    }

    /**
     * The percentage of neutron to reflect when a stream hits a reflector column.
     */
    public static double getReflectorEfficiency() {
        return NtmConfig.COMMON.DIAL_REFLECTOR_EFFICIENCY.get();
    }

    /**
     * Whether fuel rods should deplete, disabling this makes rods last forever
     */
    public static boolean getDepletion() {
        return !NtmConfig.COMMON.DIAL_DISABLE_DEPLETION.get();
    }

    /**
     * Whether xenon poison should be calculated
     */
    public static boolean getXenon() {
        return !NtmConfig.COMMON.DIAL_DISABLE_XENON.get();
    }
}
