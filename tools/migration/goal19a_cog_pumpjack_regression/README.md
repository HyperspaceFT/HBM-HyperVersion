# Goal19A stray cog and pumpjack regression

Run `python -B -X utf8 tools/migration/verify_goal19a_cog_pumpjack.py` from the NEO repository with the existing Python and JDK 21 (found as `verify_goal8.py` finds it). Each run writes its commands, compiler output and assertions to `build/migration/goal19a/cog-pumpjack/<run>/result.log` and a summary to `report.json` there. `--no-mutations` runs only the baseline. The report carries the provenance `package_goal17b.verify_report`/`package_goal18b.verify_report` check: `source_sha256` (every production file compiled in either world, hashed before the run), `fixture_sha256` (the regression Java files, the accessor, this driver and every `tools/migration` module it imported, hashed after the runs), `source_stable_after_run`, the baseline javac/java `commands`, `cog_pumpjack_counts`, `mutations_detected`, and per mutation its javac/java commands with the detecting world last; a mutation counts only when javac returned 0 and that java run failed with an AssertionError. No Gradle task is run.

## Production code under test

- Cog world: the Goal 8 world unchanged (`goal8_regression/stubs.py`, `verify_goal8.PRODUCTION`), with the production `StrayCog` driven through the unchanged accessor `goal8_regression/.../Goal8CogAccess.java` (hit handlers, NBT hooks, gravity). Fixture: `com/hbm/entity/projectile/Goal19ACogRegression.java`.
- Pumpjack world: the Goal 11A machine world (`goal11a_regression/stubs.py`, `verify_goal11a.PRODUCTION`, AnvilRecipes without its Goal 13A block as there) plus the production `MachinePumpjackBlockEntity`. `stubs.py` adds only its block entity type and `Direction.getCounterClockWise(Axis)` (Y only, as the world's `getClockWise(Axis)`). The core state comes from the production `DummyableBlock.createCoreState` of the compiled derrick block; `MachinePumpjackBlock` is not compiled. Fixture: `com/hbm/blockentity/machine/oil/Goal19APumpjackRegression.java`.

## Behaviour checked

Reference: original d31426c `EntityCog` (`onUpdate` is only `super.onUpdate()`; `onImpact` lays down, bounces or explodes only `orientation < 6` cogs) and `TileEntityMachinePumpjack.getPorts`.

1. A slow upright top-face hit lies the cog down unchanged: orientation + 6, on the hit point, stuck, no blast or block break.
2. When its support changes, the cog comes loose and stays lying (orientation 9) on every later server tick; a client copy likewise.
3. A loose lying cog re-landing on a top face moves onto the hit point and sticks to the new block with its orientation unchanged, without explosion or block removal even above speed 0.75; then it only base-ticks.
4. A lying cog hitting an east, west, north, south or bottom face (speed 0.3 and 1.2) only loses its motion: not stuck, no stuck block, in place, still lying, falling on the next tick.
5. NBT: a loose lying cog saves `rot` 9 and `inGround` false and keeps falling lying after a reload; a lying cog in the ground reloads in the ground.
6. Upright cogs keep their orientation in flight; a fast upright hit still bounces, explodes and breaks the block.
7. Pumpjack, all four facings: the four `getConPos` entries equal the original ports plus their face, `(rot*2 +- dir*2, +-dir)` and `(rot*4 +- dir*2, +-dir)` in that order, with the original `ForgeDirection.getRotation(DOWN)` written out; each lies two blocks off the machine axis and points away from it; NORTH/SOUTH equal the former NEO list, EAST/WEST differ from it.

## Mutations

Each is applied to a temporary copy of `src/main/java`; the copy must compile and a fixture assertion must fail: the restored server-side stand-up correction in `tick()`; the lying re-landing without `setPos`; a lying cog sticking on a side or bottom face; a lying cog exploding on a fast landing; the former pumpjack entries 2-4.

## Not covered

Real ray tracing, collisions, drag and the projectile physics of `ProjectileNT` (its stand-in only counts flight ticks and applies gravity), entity data synchronisation to clients, cog rendering, `MachinePumpjackBlock` placement and its proxies, real energy/fluid network connections through the corrected east/west points, dedicated servers and gameplay.
