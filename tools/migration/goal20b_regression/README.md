# Goal20B isolated verification

Two verifiers cover the Goal20B gas centrifuge batch: the machine (pseudo-fluid cascade, overclocking upgrade, persistence and sync) with a finite uranium-fuel-rod ledger, and the acquisition and resources (assembly `ass.gascent`, the pseudo-fluid table, the upgrade and enriched ZIRNOX rod recipes, the fifteen language keys, the six imported assets, the provider and registration edits and the generated files). They reuse the older isolated worlds without modifying them. Only the output roots, the fixtures, the stub layer, the static module and the mutations belong to Goal20B. Run them from the NEO repository with the existing Python 3 and JDK 21; they need no Gradle, game, server or network:

- `python -B -X utf8 tools/migration/verify_goal20b_machine.py [--mutations]`
- `python -B -X utf8 tools/migration/verify_goal20b_recipes.py [--mutations]`

Always pass `-B`. Without it, the imports leave `__pycache__` bytecode caches in the reused older `tools/migration/goal*_regression` packages.

Outputs go to unique directories under `build/migration/goal20b/<machine|recipes>/`. Each report records the exact commands and exit codes, the SHA-256 of the production sources, fixtures, stubs, adapters and JDK binaries, and `source_stable_after_run` (sources hashed again after the run). A mutation counts only after its temporary copy compiles (where compiled) and the run then fails with the expected `AssertionError` fragment.

**The gas centrifuge and the reactor only ever run inside the stub world.** Compilation and isolated services never prove game, save, GUI, JEI, rendering, multiplayer or dedicated-server acceptance.

## Machine

`verify_goal20b_machine.py` reuses the Goal19C machine world unchanged (`verify_goal19c_machine.py` production set, `goal19c_regression/machine_stubs.py`, the Goal19C fixtures) and compiles the production `MachineGasCentrifugeBlockEntity` (with its `PseudoFluidTank`), `GasCentrifugeRecipes` and `MachineGasCentrifugeMenu` beside `goal20b_regression/com/hbm/blockentity/machine/Goal20BMachineRegression.java`. `goal20b_regression/machine_stubs.py` adds, by anchored replacement of Goal19C stand-ins:
- the registry holders the machine names (block entity and menu types, the centrifuge loop sound, the upgrade and nugget/fluorite items; stack sizes checked statically against `NtmItems.java`);
- `MachineUpgradeItem` with type/tier and the production `UpgradeType` enum verbatim;
- `UF6`, `PUF6` and `WATZ` in the `Fluids` stand-in (stand-in ids 45-47);
- `Level.hasChunkAt` over declared unloaded positions;
- the vanilla `BlockPos.north/south/east/west` and `ItemStack.matches` bodies from the NeoForge sources jar;
- the production `Library.chargeTEFromItems` body.

Every scenario calls the production `updateEntity()` once per tick on a manual clock, beside an independent model of the original `TileEntityMachineGasCent.java:180-233` (d31426c); production constants are read reflectively so a mutated class is seen. Sections:
1. constants: power, speeds (150/80), consumption (200/300), tanks (2,000; 8,000), the 600 mB tail, slots; the eight pseudo fluids in declaration order with their numbers and outputs (`MUD`/`MUD_HEAVY` outputs deferred); `fluidConversions` = {UF6 → NUF6, PUF6 → PF6}; the three summary rows;
2. feed and gates: conversion without power and within the tank room; power 0, exactly 200 k and 199; input below the consumed amount; a full output tank; full output slots; HEUF6 without the upgrade; MUD never enriches; identifier retypes only for conversion keys; battery charge; automation slot rules;
3. cycles: every pseudo fluid with and without the upgrade, tick by tick, and the slot merge order;
4. cascades: the 10-tick target `core.relative(FACING.getOpposite())` in all four facings, the 599/600 mB tail, a full target, a target with another real fluid, an unloaded neighbour; two machines (6 U238, 6 uranium fuel nuggets, 4 fluorite, 180,000 HE), four upgraded machines (11 U238, 1 U235, 4 fluorite, 240,000 HE), one machine (3 U238, 900 mB LEUF6 left) and 900 mB PUF6 (3 Pu238, 6 Pu mix, 3 fluorite, 90,000 HE), each machine equal to the model every tick;
5. persistence and sync: the NBT keys and types, round trips mid-cycle and after a PUF6 retype, a tag without `tank_max`, the packet layout and the type-before-fill client order, client audio, packets and dirty marking;
6. finite ledger: the static chemical-plant steps (parsed from the production sources), two isolated cascades per uranium fuel rod, the static nugget → billet → rod crafting, and 24 `URANIUM_FUEL` rods in the Goal19C ZIRNOX/turbine/condenser/socket chain until steady plus a 2,000-tick window, compared with the Goal19C natural uranium figures.

The run writes `finite.json`, `finite_ticks.csv`, `cascades.json` (every enrichment, transfer and tail with its tick), `notes.json` and `static-chain.properties` next to `report.json`. `--mutations` applies ten anchored edits (speed 140, consumption 250, tail 500, period 5, high-speed gate removed, conversion requires power, LEUF6 produces 300, packet fills after names, no `tank_max` workaround, transfer false when nothing moved).

## Recipes and resources

`verify_goal20b_recipes.py` compiles the live `AssemblyMachineRecipes` and the frozen Goal20B-start copy (`build/migration/goal20b/baseline-files`, package `goal20b.base`) over the inherited Goal19C recipe-world stand-ins with `goal20b_regression/Goal20BRecipeRegression.java`: in both `ENABLE_528` modes the live table is the frozen table plus `ass.gascent` right after `ass.centrifuge` (48 → 49 and 44 → 45 rows), with the numbers parsed from the original `AssemblyMachineRecipes.java:282-283`; `ass.cirnox` still serialises as `migration/goal19c-assembly-recipes.json` records. It exports `goal20b-assembly-catalog.json` and `goal20b-assembly-recipes.json` (the `goal19c-assembly-recipes.json` shape).

`goal20b_regression/recipe_static.py` checks, without execution:
- the production `GasCentrifugeRecipes` table, conversions and summary rows against the original `GasCentrifugeRecipes.java:24-34,94-101` (MUD outputs, WATZ conversion and the WATZ row deferred);
- the fifteen language keys in `NtmLanguageProvider`, `zh_cn.json` and `zh_cn-map.json` (13 upstream against the original `en_US.lang`/`zh_CN.lang` lines, 2 local), each file changed only by these keys against the frozen start, and the totals (zh 2,236, map 2,344, deferred 108);
- the six asset copies byte-identical to the originals, the OBJ objects `Flag` and `Centrifuge`, the 256×256 GUI sheet and the `block_steel` particle texture;
- the provider and registration files differing from the frozen start by insertions only, with the expected lines;
- the provider crafting statements (upgrade `GNG/RUR/GMG`, uranium fuel and U235 rods) against the original `CraftingManager.java:728` and `RodRecipes.java:28,34`;
- the generated files read at run time: the three recipes and their advancements, the blockstate, the particle and item models, the loot table, the pickaxe tag and the fifteen English keys (en total 2,344). A missing generated file fails the run with a clear message after every other check (rerun after `runData`).

Mutations (`--mutations`): compiled assembly edits (row dropped, duration 300, analog circuit) and static copies (MEUF6 consumption, a summary row count, a removed Chinese key, a mapping kind, a provider English text, a corrupted GUI texture, rod billet count 3, rod META, upgrade pattern), plus three generated-file copies when the generated tree holds the files.

Not covered: the game, real chunks and NBT encoding, the GUI, JEI, rendering, multiplayer, the dedicated server, `MachineGasCentrifugeBlock` placement and removal (structure checked statically only), and the chemical-plant and crafting steps as runtime (static only).
