# Goal19B isolated verification

Four verifiers cover the standard industrial steam turbine (`machine_industrial_turbine`). They reuse older isolated worlds without modifying them; only the output roots, the fixtures, the stub additions and the mutations are Goal19B's own. Run from the NEO repository with the existing Python 3 and JDK 21 (no Gradle, game, server or network):

- `python -B -X utf8 tools/migration/verify_goal19b_machine.py`
- `python -B -X utf8 tools/migration/verify_goal19b_structures.py`
- `python -B -X utf8 tools/migration/verify_goal19b_recipes.py`
- `python -B -X utf8 tools/migration/verify_goal19b_resources.py --source ../Hbm-s-Nuclear-Tech-GIT`

Always pass `-B`: the imports otherwise leave `__pycache__` bytecode caches in the reused older `tools/migration/goal*_regression` packages. Outputs stay under unique directories in `build/migration/goal19b/<machine|structures|recipes|resources>/`. Each report records the exact commands and exit codes and the SHA-256 of the extracted production sources, fixtures, stubs, adapters and JDK binaries; sources are hashed again after each run (`source_stable_after_run`). A mutation counts only after its temporary copy compiles and the run fails with the expected `AssertionError` fragment. Compilation and isolated services never prove game, save, GUI, rendering, audio, multiplayer or dedicated-server acceptance.

## Machine

`verify_goal19b_machine.py [--mutations]` compiles the production `MachineIndustrialTurbineBlockEntity` and `TurbineBaseBlockEntity` into the unchanged Goal 9B world with the existing JDK 21 only. That world holds the production boilers, firebox, condenser, ducts, barrels, red cables, battery socket, UniNodespace and PowerNetMK2. The run writes `build/migration/goal19b/machine/<id>/`:
- `report.json`: commands, exit codes, `source_stable_after_run`, and the SHA-256 of the sources, fixtures, stubs and JDK;
- `result.log`;
- `finite.json`;
- `sources.txt`.

`machine_stubs.py` only adds, by anchored replacement of Goal 9B stand-ins:
- the `MACHINE_INDUSTRIAL_TURBINE` and `TURBINE_LARGE_LOOP` refs;
- a settable client player through `NuclearTechMod.proxy.me()`, with the vanilla 1.21.1 `distanceToSqr(double, double, double)` body;
- a recording `AudioWrapper` with the production float-position overload.

No stand-in shadows a compiled production source. Expected numbers come from the original d31426c (`TileEntityMachineIndustrialTurbine.java:34-36,42,81-148,171-226`, `TileEntityTurbineBase.java:47-130`, `Fluids.java:637-640`) or from independent models in the fixture.

Sections:
1. constants;
2. op formula;
3. flywheel (spool-up, idle drain, low input, tier maxPower);
4. lever;
5. persistence and reload continuation;
6. sync payload;
7. dirty marking;
8. client rotor and audio;
9. ports and real duct/cable transfer for four facings;
10. a finite coal -> firebox -> heat boiler -> turbine -> condenser -> water loop;
11. the high tiers (isolated only).

Section 10 checks these ledgers on every tick, with a reload partway through:
- water: `100 x (water + spent) + steam` stays constant;
- HE: `200 x ops == flywheel + released` and `released == socket gain + discarded`;
- steam and spent steam;
- fuel and heat, kept separate from HE. Firebox and boiler post-states must equal rules written out from the original (`TileEntityHeaterFirebox`, `TileEntityFireboxBase`, `ModuleBurnTime`, `TileEntityHeatBoiler`, `Fluids.java:626-630`), never from the production methods:
  - firebox: offered = produced + capped, and Δheat = produced − moved − decayed;
  - boiler: Δheat = moved − spent − decayed − capped;
  - spent = 200 TU per mB of water boiled, and steam made = 100 mB per mB.

`heatBranches()` covers the firebox and boiler cap and decay branches the chain never reaches. `finite.json` records the fuel, `heat_TU`, water boiled and steam made, `neo_anchors` and `original_heat_anchors`. The original heat boiler's post-impact heating (`TileEntityHeatBoiler.java:83-86`, `TomSaveData` fire) has no NEO counterpart and is not modelled.

`--mutations` applies 23 anchored edits to a copy of the turbine block entity. Each must compile, then fail its section with the expected assertion; a crash is not a detection. Every mutation command record keeps its combined `output`.

Not covered:
- `MachineIndustrialTurbineBlock` (see the structure harness), `RenderIndustrialTurbine`;
- port proxies (ducts and cables connect at the DirPos directly);
- real audio playback, NeoForge tick order and chunk loading, network timing;
- payload codecs, dedicated servers and gameplay.

## Structures

The structure world extends the Goal18A world (18A → 17B → 16B → 16A → 15B → 14C → 14B) unchanged. It extracts the production `MachineIndustrialTurbineBlock` `getDimensions`/`getOffset`/`newBlockEntity`/`fillSpace`/`useWithoutItem`, the block entity's `getConPos`/`getPowerPos`, and `DummyableBlock` `neighborChanged`/`destroyIfOrphan`. The turbine overrides neither `onRemove` nor `playerWillDestroy` (checked by regex and reflection), so teardown is the inherited chain plus the orphan cascade; the stand-in `Level.setBlock` sends the flag-1 neighbour update after `onRemove`.

Expected values come from the original (dims `{2,0,3,3,1,1}`, offset 3, the `getAllPorts` table, the tile entity's port definitions, `onBlockActivated`) or from independent fixture models: the rotation table, the 63-cell footprint, the dummy-chain parent, and the original `BlockDummyable.rotatePorts` including its final `port += facing * -getOffset()` shift (`BlockDummyable.java:624-628`, added by `e6d3e83fe`/`7df08fde1` after `7f74257e1` introduced the table). With that shift the original's placed-block loop lands on the seven core-relative cells NEO places, in all four facings; the unshifted `7f74257e1` intermediate is checked only as a documented difference (three ports outside the box, four shifted by 3·facing). Engine facts (`InteractionResult.sidedSuccess`, `Vec3.atCenterOf`, the `removeBlock` flags, the flag-1 neighbour update and `onRemove` running before it) are confirmed against the NeoForge sources jar.

Covered: the footprint per facing; exactly seven extras with fluid+power proxies and no inventory, 55 plain dummies and one core; six fluid connections and the power connection outside the box, each adjacent to exactly one port, with the power connection facing back; placement refunds on any blocked cell; teardown of the whole structure from any cell with exactly one survival drop on the player path (none on direct removal or for a creative player); neighbouring turbines, foreign cores and replacement blocks survive; the unloaded-chunk guard; `useWithoutItem` for every cell × sneaking × side × operational × facing (lever sound, pull count, red locked message, interaction results, missing or foreign core). 17 mutations (`dims_side_3_to_2`, `offset_3_to_2`, `drop_one_makeExtra`, `p7_without_above`, `fill_rot_opposite_facing`, `lever_offset_3_to_2`, `lock_inverted`, `new_block_entity_extra_null`, `sneak_gate_removed`, `missing_core_passes`, `lever_volume_1_5_to_1`, `lever_sound_event_swapped`, `lever_sound_at_core`, `lever_message_not_red`, `conpos_rot_2_to_1`, `conpos_top_above_3_to_2`, `powerpos_direction_facing`).

Not covered: the block entity tick/NBT/sync/audio/render box (machine verifier), `ProxyComboBlockEntity.canConnect` delegation, `getTicker`, the codec, tooltip and overlay, the real `BlockItem.place` and neighbour-update ordering, hitboxes, loot content.

## Recipes

`verify_goal19b_recipes.py` compiles the live `AssemblyMachineRecipes` and the frozen copy from the 19B start commit `70bc9899` (package `goal19b.base`, cross-checked against `build/migration/goal19b/baseline.json` and `baseline-files/`) over the inherited 18B/18A stand-ins plus `Goal19BRecipeRegression.java`, and runs both `ENABLE_528` modes. The live catalog must equal the frozen catalog plus exactly one row, `ass.iturbine`, appended last (46→47 rows with 528 off, 42→43 with 528 on); every base row is byte-identical in the 18B serialization and order, and the blueprint pool state is unchanged. The new row's numbers (200 ticks, 100 HE/t, six inputs, one output) are parsed from the original `AssemblyMachineRecipes.java:434-436` into `original-ass-iturbine.json`; item ids, the `c:plates/steel` tag and the GOLD dense wire meta (7900, original `Mats.MAT_GOLD`) are checked against the production registrations, with `ass.turbofan`, `ass.coker` and `ass.combustiongen` as precedents. The run exports `goal19b-assembly-catalog.json` (the new row in both modes), from which `migration/goal19b-assembly-recipes.json` is taken. `recipe_stubs.py` declares no new stand-in; it anchors the inherited ones and fails on a shadowed production source. Mutations: `registration_dropped`, `steel_plates_16_to_15`, `duration_200_to_100`, `rubber_ingot_replaced_by_copper_ingot`, `dense_wire_gold_to_copper`, `output_count_1_to_2`.

`verify_goal18b_recipes.py` fails by design on the Goal19B tree at `Goal18BRecipeRegression.java:307` (`assemblyUnchanged`: "every Goal18A assembly row is retained byte for byte and none is added"), which runs after all of its crystallizer coverage; the Goal19B recipe verifier proves the retained rows instead. `verify_goal18a_recipes.py` keeps failing first at its 28-row literal.

## Resources

`verify_goal19b_resources.py --source <original>` checks the three imported assets byte-for-byte against the original (the OBJ holds exactly `Turbine`, `Gauge` and `Flywheel`), the generated tree against the `goal19a` JAR and the frozen 19B start (only the four new files, `en_us.json`, `sounds.json`, the pickaxe tag and the stamp may differ), the three bilingual keys and their mapping entries (CRLF, no BOM, sorted keys, 108 deferrals unchanged), the twelve source wiring sites (each exactly once) and the generation stamp (inputs and fingerprints recomputed read-only from `gradle/migration-resources.gradle`). It has no mutation set.
