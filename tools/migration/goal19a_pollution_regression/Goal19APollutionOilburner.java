package com.hbm.blockentity.machine;

import com.hbm.blockentity.machine.heater.HeaterOilburnerBlockEntity;
import com.hbm.handler.pollution.PollutionHandler;
import com.hbm.handler.pollution.PollutionHandler.PollutionType;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.fluid.trait.FT_Polluting;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.level.Level;

import java.util.ArrayList;
import java.util.List;

/**
 * Goal19A oil burner pollution over the production HeaterOilburnerBlockEntity in the Goal 11A machine world.
 * Original d31426c: TileEntityHeaterOilburner.java:39 (super(3, 100): 100 mB smoke tanks), :70-79 (toBurn = min(setting, fill);
 * every 5 ticks while toBurn > 0 pollute(type, BURN, toBurn * 5)); TileEntityMachinePolluting.java:38-62.
 */
public class Goal19APollutionOilburner {
    static int checks, scenarios, ticks;
    static void check(boolean condition, String message) { if(!condition) throw new AssertionError(message); checks++; }

    /** Original soot rates: SOOT_PER_SECOND = 1F / 25F; SOOT_UNREFINED_OIL * 0.1F (OIL, HEATINGOIL: P_OIL), SOOT_GAS * 0.005F (GAS: P_GAS). */
    static final float ORIGINAL_SOOT_UNREFINED_OIL = 1F / 25F * 0.1F, ORIGINAL_SOOT_GAS = 1F / 25F * 0.005F;
    /** mB per call for toBurn 1..10, precomputed in float32 from the original formula (OIL rounds the float32 2.0000002 up to 3 at toBurn 1). */
    static final int[] OIL_MB = {0, 3, 5, 6, 9, 10, 12, 14, 17, 18, 20};
    static final int GAS_MB = 1;

    /** TileEntityMachinePolluting.pollute(FluidType, BURN, int toBurn * 5) then pollute(PollutionType, value * amount). */
    static int originalMb(float value, int toBurn) {
        float amount = toBurn * 5;
        float perType = value * amount;
        return (int) Math.ceil(perType * 100);
    }

    /** The original 100 mB smoke tank without an outlet: returns the world pollution of one call and updates the fill. */
    static float originalTankCall(int[] fill, int mB) {
        fill[0] += mB;
        if(fill[0] > 100) { int overflow = fill[0] - 100; fill[0] = 100; return overflow / 100F; }
        return 0F;
    }

    static HeaterOilburnerBlockEntity burner(Level level, FluidType fuel, int setting, int fill) {
        Goal11ARegression.reset();
        HeaterOilburnerBlockEntity b = Goal11ARegression.burner(level, new BlockPos(0, 64, 0), Direction.NORTH);
        b.isOn = true;
        b.setting = setting;
        b.tank.setTankType(fuel);
        b.tank.setFill(fill);
        return b;
    }

    /** One tick at `time` with the heat drained first, as a consumer taking all heat; returns the heat made this tick. */
    static int tick(Level level, HeaterOilburnerBlockEntity b, int time) {
        level.time = time;
        b.heatEnergy = 0;
        b.updateEntity();
        ticks++;
        return b.heatEnergy;
    }

    static void perCall() {
        FluidType[] fuels = {Fluids.OIL, Fluids.HEATINGOIL, Fluids.GAS};
        float[] soot = {ORIGINAL_SOOT_UNREFINED_OIL, ORIGINAL_SOOT_UNREFINED_OIL, ORIGINAL_SOOT_GAS};
        long[] heat = {Goal11ARegression.OIL_HEAT, Goal11ARegression.HEATINGOIL_HEAT, Goal11ARegression.GAS_HEAT};
        for(int k = 0; k < fuels.length; k++) {
            float value = fuels[k].getTrait(FT_Polluting.class).burnMap.get(PollutionType.SOOT);
            check(value == soot[k], Goal11ARegression.fuelName(fuels[k]) + " burns the original soot rate " + value);
            for(int setting = 1; setting <= 10; setting++) {
                int expected = k < 2 ? OIL_MB[setting] : GAS_MB;
                check(originalMb(soot[k], setting) == expected, "independent original model " + Goal11ARegression.fuelName(fuels[k]) + " " + setting);
                scenarios++;
                Level level = Goal11ARegression.level();
                HeaterOilburnerBlockEntity b = burner(level, fuels[k], setting, 16_000);
                for(int t = 1; t <= 5; t++) {
                    int made = tick(level, b, t);
                    check(made == (int) (heat[k] / 1000L) * setting && b.tank.getFill() == 16_000 - t * setting,
                            "oil burner heat and fuel unchanged " + Goal11ARegression.fuelName(fuels[k]) + " setting " + setting + " tick " + t);
                    check(PollutionHandler.CALLS.size() == (t == 5 ? 1 : 0), "oil burner pollutes on the 5th tick only");
                }
                PollutionHandler.Call call = PollutionHandler.CALLS.get(0);
                check(call.type() == PollutionType.SOOT && call.amount() == expected / 100F,
                        "oil burner per-call soot ceil(value * " + setting + "mB * 5 * 100) / 100 = " + expected / 100F + " " + Goal11ARegression.fuelName(fuels[k]) + " (got " + call.amount() + ")");
            }
        }
        // Nearly empty tank: the call uses the toBurn of that tick.
        for(int[] c : new int[][] {{10, 3}, {7, 4}, {2, 1}}) {
            scenarios++;
            Level level = Goal11ARegression.level();
            HeaterOilburnerBlockEntity b = burner(level, Fluids.OIL, c[0], c[1]);
            int made = tick(level, b, 5);
            check(made == (int) (Goal11ARegression.OIL_HEAT / 1000L) * c[1] && b.tank.getFill() == 0, "nearly empty burner heat/fuel setting " + c[0]);
            check(PollutionHandler.CALLS.size() == 1 && PollutionHandler.CALLS.get(0).amount() == OIL_MB[c[1]] / 100F,
                    "oil burner nearly empty setting " + c[0] + " with " + c[1] + "mB: soot " + OIL_MB[c[1]] / 100F + " (got " + PollutionHandler.CALLS + ")");
        }
    }

    /**
     * NEO has no smoke tank; it emits the original steady state. Once the modelled original 100 mB tank is full every call
     * overflows exactly its own mB, so both agree; before that the original emits nothing (or a partial overflow on the call
     * that fills the tank) and keeps 100 mB in the tank, which NEO emits instead: the total differs by exactly 1.0 per type.
     */
    static void steadyState(String[] out) {
        for(int setting : new int[] {10, 3, 1}) {
            scenarios++;
            Level level = Goal11ARegression.level();
            HeaterOilburnerBlockEntity b = burner(level, Fluids.OIL, setting, 16_000);
            int calls = 40;
            for(int t = 1; t <= calls * 5; t++) tick(level, b, t);
            check(PollutionHandler.CALLS.size() == calls, "one call per 5 ticks setting " + setting);
            int[] fill = {0};
            int firstEqual = -1;
            float neoSum = 0F, originalSum = 0F;
            List<String> rows = new ArrayList<>();
            for(int i = 0; i < calls; i++) {
                float neo = PollutionHandler.CALLS.get(i).amount();
                boolean wasFull = fill[0] == 100;
                float original = originalTankCall(fill, OIL_MB[setting]);
                neoSum += neo;
                originalSum += original;
                if(wasFull) {
                    check(neo == original, "steady state: full original tank overflows exactly NEO's per-call amount, setting " + setting + " call " + (i + 1));
                    if(firstEqual < 0) firstEqual = i + 1;
                } else check(original < neo, "transient: the original emits less while its tank fills, setting " + setting + " call " + (i + 1));
                rows.add(neo + "/" + original);
            }
            int expectedFirst = (100 + OIL_MB[setting] - 1) / OIL_MB[setting] + 1;
            check(firstEqual == expectedFirst, "steady state starts on call " + expectedFirst + " for setting " + setting + " (got " + firstEqual + ")");
            check(Math.abs((neoSum - originalSum) - 1F) < 1e-4F, "NEO emits exactly the original 100 mB tank content (1.0) more over the run, setting " + setting + ": " + (neoSum - originalSum));
            out[0] += (out[0].isEmpty() ? "" : ",") + "{\"setting\":" + setting + ",\"mBPerCall\":" + OIL_MB[setting] + ",\"firstSteadyCall\":" + firstEqual
                    + ",\"neoTotal\":" + neoSum + ",\"originalTotal\":" + originalSum + ",\"perCallNeoOverOriginal\":\"" + String.join(" ", rows) + "\"}";
        }
    }

    public static void main(String[] args) throws Exception {
        perCall();
        String[] out = {""};
        steadyState(out);
        if(args.length > 0) java.nio.file.Files.writeString(java.nio.file.Path.of(args[0]).resolve("oilburner-steady-state.json"), "[" + out[0] + "]");
        System.out.println("Goal19A oil burner pollution: " + checks + " assertions; " + scenarios + " independent scenarios; " + ticks + " executed ticks");
    }
}
