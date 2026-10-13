package com.hbm.blockentity.machine;

import com.hbm.handler.pollution.PollutionHandler;
import com.hbm.handler.pollution.PollutionHandler.PollutionType;
import com.hbm.inventory.FluidContainerRegistry;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.fluid.trait.FT_Polluting;
import net.minecraft.core.Direction;
import net.minecraft.world.level.Level;

/**
 * Goal19A turbofan pollution over the production MachineTurbofanBlockEntity in the Goal17B machine world.
 * Original d31426c: TileEntityMachineTurbofan.java:187-214 (amountToBurn = min(1 + afterburner, fill); every 20 ticks while
 * burning pollute(type, BURN, amountToBurn * 5)); TileEntityMachinePolluting.java:38-62 (per burn entry
 * pollute(type, value * amount): ceil(amount * 100) mB into the 150 mB buffer, overflow / 100 to the world).
 */
public class Goal19APollutionTurbofan extends Goal17BMachineRegression {
    /** Original Fluids.java SOOT_REFINED_OIL = SOOT_PER_SECOND * 0.025F with PollutionHandler SOOT_PER_SECOND = 1F / 25F. */
    static final float ORIGINAL_SOOT_REFINED_OIL = 1F / 25F * 0.025F;
    /** mB per 20-tick call for amountToBurn 1..4, precomputed in float32 from the original formula. */
    static final int[] EXPECTED_MB = {0, 1, 2, 2, 3};

    /** TileEntityMachinePolluting.pollute(FluidType, BURN, int amountToBurn * 5) followed by pollute(PollutionType, float). */
    static int originalMb(float value, int amountToBurn) {
        float amount = amountToBurn * 5;
        float perType = value * amount;
        return (int) Math.ceil(perType * 100);
    }
    static int originalPower(int burned, int afterburner) {
        return (int) (3850L * burned * (1 + Math.min(afterburner / 3D, 4)));
    }

    static void perCall() {
        fresh();
        float soot = Fluids.KEROSENE.getTrait(FT_Polluting.class).burnMap.get(PollutionType.SOOT);
        check(soot == ORIGINAL_SOOT_REFINED_OIL, "kerosene burns the original SOOT_REFINED_OIL " + soot);
        for(int burned = 1; burned <= 4; burned++) check(originalMb(ORIGINAL_SOOT_REFINED_OIL, burned) == EXPECTED_MB[burned], "independent original model " + burned + "mB");
        for(int a = 0; a <= 3; a++) {
            for(int fill : new int[] {2000, 1, 2, 3}) {
                if(fill != 2000 && fill >= a + 1) continue;
                scenario();
                Level l = fresh();
                var b = turbine(l, 0, Direction.NORTH, a, Fluids.KEROSENE, fill);
                int burned = Math.min(a + 1, fill);
                l.time = 18;
                step(l, b);
                check(b.smoke.getFill() == 0 && b.output == originalPower(burned, a) && b.consumption == burned && b.tank.getFill() == fill - burned,
                        "A" + a + " fill" + fill + " off-20 tick: no smoke, unchanged power/fuel");
                if(b.tank.getFill() < burned) continue;
                int before = b.tank.getFill();
                step(l, b);
                check(b.smoke.getFill() == EXPECTED_MB[burned] && b.smokeLeaded.getFill() == 0 && b.smokePoison.getFill() == 0 && PollutionHandler.CALLS.isEmpty(),
                        "turbofan per-call soot ceil(value * " + burned + "mB * 5 * 100) = " + EXPECTED_MB[burned] + " A" + a + " fill" + before + " (got " + b.smoke.getFill() + ")");
                check(b.output == originalPower(burned, a) && b.power == 2L * originalPower(burned, a) && b.tank.getFill() == before - burned,
                        "power and fuel unchanged by pollution A" + a);
            }
        }
        // Nearly empty tank: the 20-tick call uses this tick's amountToBurn, not 1 + afterburner.
        for(int[] c : new int[][] {{3, 1}, {3, 2}, {3, 3}, {2, 1}, {2, 2}, {1, 1}}) {
            scenario();
            Level l = fresh();
            var b = turbine(l, 0, Direction.NORTH, c[0], Fluids.KEROSENE, c[1]);
            l.time = 19;
            step(l, b);
            check(b.smoke.getFill() == EXPECTED_MB[c[1]] && b.consumption == c[1] && b.tank.getFill() == 0 && b.output == originalPower(c[1], c[0]),
                    "turbofan nearly empty A" + c[0] + " " + c[1] + "mB left: soot " + EXPECTED_MB[c[1]] + " (got " + b.smoke.getFill() + ")");
        }
    }

    static void bufferAndOverflow() {
        scenario();
        Level l = fresh();
        var b = turbine(l, 0, Direction.NORTH, 3, Fluids.KEROSENE, 24000);
        for(int call = 1; call <= 52; call++) {
            l.time = 20 * call - 1;
            step(l, b);
            check(b.tank.getFill() == 24000 - 4 * call && b.output == 30800, "turbofan buffer run fuel/power call " + call);
            if(call <= 50) check(b.smoke.getFill() == 3 * call && PollutionHandler.CALLS.isEmpty(), "turbofan A3 150mB buffer fills 3mB per call, no world pollution, call " + call);
            else check(b.smoke.getFill() == 150 && PollutionHandler.CALLS.size() == call - 50 && PollutionHandler.CALLS.get(call - 51).amount() == 3 / 100F
                    && PollutionHandler.CALLS.get(call - 51).type() == PollutionType.SOOT, "turbofan full buffer overflows the whole 3mB as 0.03 call " + call);
        }
        for(int[] c : new int[][] {{3, 149, 2}, {1, 149, 1}, {1, 148, 0}, {0, 149, 0}}) {
            scenario();
            l = fresh();
            b = turbine(l, 0, Direction.NORTH, c[0], Fluids.KEROSENE, 2000);
            b.smoke.setFill(c[1]);
            l.time = 19;
            step(l, b);
            boolean ok = b.smoke.getFill() == Math.min(150, c[1] + EXPECTED_MB[c[0] + 1]);
            ok &= c[2] == 0 ? PollutionHandler.CALLS.isEmpty() : PollutionHandler.CALLS.size() == 1 && PollutionHandler.CALLS.get(0).amount() == c[2] / 100F;
            check(ok, "turbofan A" + c[0] + " buffer " + c[1] + " exact overflow " + c[2] + "mB");
        }
    }

    public static void main(String[] args) {
        FluidContainerRegistry.register();
        perCall();
        bufferAndOverflow();
        System.out.println("Goal19A turbofan pollution: " + checks + " assertions; " + scenarios + " independent scenarios; " + executedTicks + " executed ticks");
    }
}
