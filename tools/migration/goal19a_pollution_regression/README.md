# Goal19A combustion pollution verification

Covers Goal19A-2 item 1 (turbofan and oil burner pollution scaled by the original call amount `burned mB * 5`) and the FLUE spill-rate correction with the `FT_Polluting` release scaled by the released mB. Run from the NEO repository with the existing Python 3 and JDK 21:

- `python -B -X utf8 tools/migration/verify_goal19a_pollution.py`

Output goes to a unique `build/migration/goal19a/pollution/<run-id>/` with `report.json`, one directory per world (`compile.log`, `run.log`, generated stand-ins) and one directory per mutation. The real NeoForge sources cache is required; the original repository is read (never written) to confirm the facts the fixtures encode (`original_facts`).

No new world is built; `worlds.py` assembles three existing ones without changing their modules:

- turbofan: the Goal17B machine world with the production `MachineTurbofanBlockEntity`; kerosene carries the production `P_FUEL` chain, `PollutionHandler` records every call. `Goal19APollutionTurbofan` checks the 20-tick per-call mB at A0..A3 and nearly empty tanks against the original formula (`ceil(value * amountToBurn * 5 * 100)`, precomputed in float32), unchanged power and fuel, the 150 mB buffer filling over 50 A3 calls and exact overflow / 100.
- oilburner: the Goal 11A machine world with the production `HeaterOilburnerBlockEntity`; OIL, HEATINGOIL and GAS carry their production `P_OIL`/`P_GAS` chains. `Goal19APollutionOilburner` checks settings 1..10 and nearly empty tanks (`ceil(value * toBurn * 5 * 100) / 100` every 5 ticks), unchanged heat and fuel, and compares NEO's direct emission with a modelled original 100 mB tank: from the first call after the tank is full both agree exactly; before that the original emits nothing (or a partial overflow on the call that fills the tank) and keeps 100 mB, so NEO's total is exactly 1.0 higher per pollution type over a run. The per-call table goes to `oilburner/oilburner-steady-state.json` and the report.
- traits: the Goal19A barrel world with the production `FT_Polluting` and `FluidTrait.onRelease`; `Goal19AFlue` is generated from the production FLUE row of `Fluids.java` (with `SOOT_GAS` substituted by its production definition). `Goal19APollutionTraits` checks the FLUE burn and spill maps and SPILL/BURN/VOID releases at 1, 7 and 250 mB, directly and through `FluidTrait.onRelease`.

Mutations (each compiled against the world's classes and required to fail a named assertion): turbofan unscaled, turbofan amount without `* 5`, oil burner unscaled, oil burner `toBurn` without `* 5`, `FT_Polluting` SPILL and BURN ignoring `overflowAmount`, FLUE `SOOT_GAS * 25`.

None of this is game, chunk-pollution, sound, client, save or dedicated-server acceptance.
