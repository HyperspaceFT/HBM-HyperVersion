# Goal20A isolated verification

Two verifiers cover the Goal20A front end: the sulfuric acid uranium/thorium crystallizer rows, the yellowcake billet input, the thorium smelting recipes, the TH232 ZIRNOX breeding rod recipe and the breeding behaviour of the existing reactor. They reuse the older isolated worlds without modifying them. Only the output roots, the fixtures, the static module and the mutations belong to Goal20A. Run them from the NEO repository with the existing Python 3 and JDK 21; they need no Gradle, game, server or network:

- `python -B -X utf8 tools/migration/verify_goal20a_recipes.py [--mutations]`
- `python -B -X utf8 tools/migration/verify_goal20a_machine.py [--mutations]`

Always pass `-B`. Without it, the imports leave `__pycache__` bytecode caches in the reused older `tools/migration/goal*_regression` packages.

Outputs go to unique directories under `build/migration/goal20a/<recipes|machine>/`. Each report records the exact commands and exit codes, the SHA-256 of the production sources, fixtures, stubs, adapters and JDK binaries, and `source_stable_after_run` (sources hashed again after the run). A mutation counts only after its temporary copy compiles (where compiled) and the run then fails with the expected `AssertionError` fragment.

**The reactor only ever runs inside the stub world.** Compilation and isolated services never prove game, save, GUI, JEI, multiplayer or dedicated-server acceptance; see `migration/GOAL20A-ACCEPTANCE.md`.

## Recipes

`verify_goal20a_recipes.py` compiles the production `CrystallizerRecipes` (41 default rows) over the inherited Goal18A/18B recipe-world stand-ins (`goal18b_regression/recipe_stubs.py`, real Gson) with `goal20a_regression/Goal20ARecipeRegression.java`:
- rows 1-36 equal the frozen Goal18B export `migration/goal18b-crystallizer-recipes.json`; rows 37-41 are `ore_uranium`, `ore_uranium_deepslate`, `ore_uranium_scorched` (→ `crystal_uranium`) and `ore_thorium`, `ore_thorium_deepslate` (→ `crystal_thorium`), 1 block + 500 mB sulfuric acid, 600 ticks, productivity 0.05;
- the expected numbers are parsed from the original `CrystallizerRecipes.java:59,67,68` and `OreDictManager.java:347,351` (read-only);
- the new rows resolve only under sulfuric acid; crystals, powders, ingots, the plutonium nether ore, deepslate and the unnamed gneiss/nether uranium ores resolve to nothing;
- JSON round trip, packet codec, client sync and the JEI bridge carry 41 rows; a 36-row server table or custom file stays at 36 rows;
- the merge example `build/migration/goal20a/recipes/goal20a-custom-crystallizer-example.json` (published as `migration/goal20a-custom-crystallizer-example.json`) parses to the expected table;
- exports `goal20a-crystallizer-recipes.json` (41 rows) and `goal20a-default-comparison.json` (added 5, removed 0, changed 0).

`goal20a_regression/recipe_static.py` checks, without execution: the three production sources differ from the frozen Goal20A start copies (`build/migration/goal20a/baseline-files`) by exactly the declared hunks; `chem.yellowcake` is 2 uranium billets + 2 sulfur + 500 mB peroxide (original `ChemicalPlantRecipes.java:379-382`) and a custom `hbmChemicalPlant.json` replaces the whole table; the generated thorium smelting JSON (ore and powder → `ingot_th232`, 200 ticks, 0.7 experience; original `SmeltingRecipes.java:30,84`) and the absence of the retired thorium-fuel smelting files; `rod_zirnox_th232.json` (empty rod + 2 `billet_th232` → `rod_zirnox` with `hbmsntm:meta` 2, no life; original `RodRecipes.java:29,250-257`).

Mutations (`--mutations`): compiled crystallizer edits (rows dropped, acid swapped, amount halved) and static copies (yellowcake back to powder, rod billet count 3 in the generated JSON and the provider, rod META, thorium ore smelting target, smelting experience).

## Machine

`verify_goal20a_machine.py` reuses the Goal19C machine world unchanged (`verify_goal19c_machine.py` production set, `goal19c_regression/machine_stubs.py`, the Goal19C fixtures compiled beside `goal20a_regression/com/hbm/blockentity/machine/Goal20AMachineRegression.java`). Sections:
1. constants;
2. rate: a TH232 rod gains exactly k life per tick with k fuel-rod neighbours (every slot, k = 0..4), adds 0 heat (compared with a twin reactor holding coal in its place), never advances with k = 0, and breeding rods, empty slots, depleted rods and non-rod items do not count;
3. replacement: the slot becomes a fresh `THORIUM_FUEL` rod (META 3, life 0, no custom data) on the step that makes life exceed 20,000 and the remaining steps of that tick are skipped; later slots see it the same tick, earlier slots from the next tick; k = 1 from life 0 replaces on tick 20,001;
4. persistence: `saveAdditional`/`loadAdditional` mid-breeding keep META and life and the arithmetic continues; the dirty marking fires every running tick;
5. finite: 12 natural uranium rods and 4 TH232 rods (each beside exactly two natural rods) with the Goal19B turbine/condenser chain, phase A until every TH232 rod is replaced (tick 10,001), phase B 3,000 ticks of thorium fuel; per-tick ledgers of decay steps, heat, rod life, the water constant `100 × (water + superhot + spent) + 10 × hot + steam`, turbine HE and the battery total; no meltdown.

The run writes `finite.json`, `finite_ticks.csv`, `breeding.json` and `notes.json` next to `report.json`. `--mutations` applies nine anchored edits (breeding +1 step, replace at ≥, fuelMap TH232 → depleted thorium, breeding heat, neighbour count includes breeding rods, replacement keeps life, no break after replacement, slot order reversed, TH232 maxLife 25,000).

Stand-ins beyond Goal19C: custom data is a tag held on the stand-in stack (not a real `CUSTOM_DATA` component); `ContainerHelper` saves stack copies (the block entity save/load path, not the ItemStack codec).

Not covered: the game, real chunks and NBT encoding, GUI, JEI, multiplayer, the dedicated server, and the furnace/crafting/chemical-plant steps as runtime (static only).
