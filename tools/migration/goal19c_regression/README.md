# Goal19C isolated verification

Three verifiers cover the existing ZIRNOX reactor: its ordinary acquisition (`ass.cirnox`, the rare earth chunk centrifuge row, the empty and natural uranium rod crafting recipes) and the machine completion. They reuse older isolated worlds without modifying them. Only the output roots, the fixtures, the stub additions and the mutations belong to Goal19C. Run them from the NEO repository with the existing Python 3 and JDK 21; they need no Gradle, game, server or network:

- `python -B -X utf8 tools/migration/verify_goal19c_machine.py [--mutations]`
- `python -B -X utf8 tools/migration/verify_goal19c_recipes.py [--mutations]`
- `python -B -X utf8 tools/migration/verify_goal19c_resources.py`

Always pass `-B`. Without it, the imports leave `__pycache__` bytecode caches in the reused older `tools/migration/goal*_regression` packages.

Outputs go to unique directories under `build/migration/goal19c/<machine|recipes|resources>/`. Each report records:
- the exact commands and their exit codes;
- the SHA-256 of the production sources, fixtures, stubs, adapters and JDK binaries.

Sources are hashed again after each run (`source_stable_after_run`). A mutation counts only after its temporary copy compiles and the run then fails with the expected `AssertionError` fragment.

**The reactor's meltdown is only ever triggered inside these stub worlds.** Compilation and isolated services never prove game, save, GUI, rendering, multiplayer or dedicated-server acceptance; see `migration/GOAL19C-ACCEPTANCE.md` for the disposable-world checks.

## Machine

`verify_goal19c_machine.py` works in the Goal 19B world: the 9B condenser, ducts, barrels, red cables, battery socket, UniNodespace, PowerNetMK2 and the 19B industrial turbine. Into it, it compiles:
- the production `ReactorZirnoxBlockEntity`, `ZirnoxRodItem`, `ReactorZirnoxMenu` and `HazardModifierFuelRadiation`, with `HazardEntry`, `HazardData` and `HazardModifier`;
- verbatim extractions, each checked for source equality:
  - `ReactorZirnoxBlock.neighborChanged`;
  - the `DummyableBlock` lookups and `MultiblockHandlerXR.fillSpace`;
  - the ZIRNOX `HazardRegistry` statements;
  - `HazardTypeRadiation.addHazardInformation`.

Expected numbers come from the original d31426c (`TileEntityReactorZirnox`, `ReactorZirnox`, `ContainerReactorZirnox`, `ItemZirnoxRod`, `HazardRegistry`, `HazardModifierFuelRadiation`, `HazardTypeRadiation`) or from independent models in the fixture.

Sections:
1. constants;
2. formulas (pressure, steam cycle, cooling, decay steps);
3. redstone: the 5×5×5 surface scan, rising and falling edges, the manual toggle overridden;
4. shift-click ranges, including the take-only slots;
5. persistence: NBT keys, rod `life`/META, dirty marking;
6. ports in four facings, real duct transfer, and tilt-gated provider/receiver speeds;
7. meltdown boundary, sound position and replacement;
8. rod bar width, colour and tooltip;
9. hazards: the modifier interpolation, all 21 registrations and the 1e-5 tooltip floor;
10. steady states for 1, 12 and 24 natural rods, plus the blocked-outlet meltdown control (tick 177);
11. the finite chain: ZIRNOX → industrial turbines (superhot, hot, steam) → condenser → water back to the reactor.

Section 11 checks these ledgers every tick, with a reload partway through:
- rod life equals decay steps;
- heat produced minus removed;
- `100 × (water + superhot + spent) + 10 × hot + steam` stays constant;
- per turbine, `heat × ops == flywheel + released` and `released == socket gain + discarded`.

The run writes `finite.json`, `steady.json` and `notes.json` next to `report.json`. `--mutations` applies 17 anchored edits.

Not covered:
- `RenderZirnox`, `RenderZirnoxDestroyed` and the screen (client-only, compiled by Gradle only);
- payload codecs (`CompoundTagControl` is a source check);
- NeoForge tick order and chunk loading;
- the deferred meltdown parts: debris entities, the radius-35 waste, the achievement, `radMark`, wreck radiation and fire.

A sender placed directly against a port block still fills a tilted reactor, because `ProxyComboBlockEntity` keeps the default speed. The original's `TileEntityProxyCombo` behaves the same way. The machine verifier asserts this as observed parity (`notes.json` `tilt_speed_through_proxy`).

## Recipes

`verify_goal19c_recipes.py` checks the assembly table in both `ENABLE_528` modes:
- It compiles the live `AssemblyMachineRecipes` and the frozen copy from the Goal19C start (package `goal19c.base`, from `build/migration/goal19c/baseline-files`) over the inherited recipe-world stand-ins.
- The live catalog must equal the frozen catalog plus exactly one row, `ass.cirnox`, appended last.
- The new row's numbers (600 ticks, 100 HE/t, seven inputs including 8 boron ingots) are parsed from the original `AssemblyMachineRecipes.java:524-527`.

The centrifuge check runs the production writer, parser and defaults against the 76 frozen Goal16B rows plus the new rare earth chunk row parsed from the original `CentrifugeRecipes.java:48-52`. It also covers player custom files and the append example `build/migration/goal19c/recipes/goal19c-custom-centrifuge-example.json`, which is published as `migration/goal19c-custom-centrifuge-example.json`.

Static checks cover:
- the two generated rod recipes (with no `components`, so META 0 is `NATURAL_URANIUM_FUEL`);
- the provider source;
- the material chains;
- the `ntm:any_concrete` membership against the original `ANY_CONCRETE`.

The run exports `goal19c-assembly-catalog.json`, `goal19c-centrifuge-defaults-snapshot.json` and `goal19c-centrifuge-chunk-row.json`.

Mutations (12):
- `boron_replaced_by_beryllium`, `duration_600_to_300`, `power_100_to_1000`, `concrete_16_to_12`, `registration_dropped`;
- `chunk_row_boron_2_to_1`, `chunk_row_zirconium_3_to_2`, `chunk_row_inserted_at_front`;
- static: `rod_count_3_generated`, `rod_count_3_provider`, `natural_meta_1_generated`, `natural_meta_1_provider`.

On the Goal19C tree, `verify_goal16b_recipes.py` fails by design at its 76-row assertion. The Goal19C recipe verifier proves "76 rows unchanged + 1 new row" instead. The Goal16B record files are not changed.

## Resources

`verify_goal19c_resources.py` checks the following:
- the generated tree and hand-written resources against the `goal19b` JAR and the frozen 19C start. Only these may differ:
  - `en_us.json` (exactly the 27 new keys);
  - the two rod recipes and their two advancements;
  - `zh_cn.json`;
  - the stamp.
- the 27 bilingual keys and their mapping entries, against the original `en_US.lang`/`zh_CN.lang` and `build/migration/goal19c/add_localization.py` (read, not run);
- the rod textures and models;
- each source wiring site, exactly once, including the tilt speed overrides and the radiation tooltip floor;
- the generation stamp, recomputed read-only.

It has no mutation set.
