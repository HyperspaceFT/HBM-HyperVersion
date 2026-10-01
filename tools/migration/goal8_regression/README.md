# Goal 8 isolated Stirling power regression

Run `python -B tools/migration/verify_goal8.py` with the existing Python and JDK 21. The script finds the JDK through `JAVA_HOME`, then `C:\Program Files\Java\jdk-21`, then the `PATH`. Each run writes its commands, compiler output and assertions to a distinct `build/migration/goal8/regression/<id>/result.log`, prints the checks per section and the total, and refuses to run if any stand-in would shadow a production source.

`python -B tools/migration/goal8_mutation_check.py` reverts nine Goal 8B decisions one at a time in a temporary copy of `src/main/java` and reruns the regression (log: `build/migration/goal8/mutation_check.log`). All nine must be detected. The drop decision lives in `MachineStirlingBlockEntity.getDropMeta()` (the block's `getDrops` only applies it), so the "drop meta ignores hasCog" revert is reachable from the compiled block entity.

`python -B -X utf8 tools/migration/verify_goal8_resources.py --source-only` checks the gear recipe provider, the five anvil entries, the four imported assets and the bilingual keys. Without `--source-only` (after `runData`) it also compares the generated output with `build/migration/goal8/stamp-before-g8b.json`. `package_goal8.py` checks and keeps the built JAR after that.

## Production code under test

Everything the Goal 7B regression compiles (energy and fluid networks, cables, battery socket, firebox, oven, wood burner, barrels, `MetaHelper`), plus:

- `MachineStirlingBlockEntity`;
- `StrayCog`;
- `AnvilRecipes` (the Stirling construction and recycling entries are read from the real list).

`MachineStirlingBlock` and the two renderers are not compiled: the block extends `BaseEntityBlock` through `DummyableBlock`, which the fixtures only stub, and the renderers are client-only.

## Stand-ins

`goal8_regression/stubs.py` starts from the Goal 7B stand-ins and then:

- registers the engine's block entity type and the `WARN_OVERSPEED`/`UPGRADE_PLUG` sounds as identities, and adds `Direction.getCounterClockWise` with the vanilla mapping;
- records world effects on the level instead of simulating them: played sounds (event, position, source, volume, pitch), `ExplosionVNT` explosions (exploder, position, strength, fire, block damage) and added entities; `PacketDistributor.sendToPlayersNear` records its payloads. The explosion's block-damage flag is the `isSmoking` argument, because production `ExplosionVNT.newExplosion` only allocates and processes blocks when it is set;
- gives `BlockState` a settable explosion resistance;
- replaces `ProjectileNT` with a minimal entity: position, motion, `tickCount`, synched data, discard and damage plumbing. Its `tick()` only counts a flight step and applies the `getDefaultGravity()` hook; ray tracing, drag and water are not modelled. StrayCog's own handlers are driven directly with hit results;
- merges the Goal 3A/5A anvil stand-ins into this chain: `RecipesCommon` keeps the production `ComparableStack` meta rule (`(item)`/`(item, count)` are meta wildcards, `(item, count, meta)` is exact) and matches `TagStack` by a plain string tag on the item; the smithing recipes and `InventoryUtil` are inert;
- adds the registry names `AnvilRecipes` uses to `NtmItems`/`NtmBlocks`, `ItemTags.PLANKS`, and a few inert player/menu/inventory methods.

The heat source interface `api.hbm.tile.IHeatSource` is the chain's two-method stand-in with the production signatures. The older Goal 3A/5A anvil suites only gained the inert `ItemTags.PLANKS` declaration so they still compile the changed `AnvilRecipes`; their assertions are unchanged.

## Sections

1. Heat intake and power: 10 % pull from a real firebox below the core, integer truncation (5 TU -> no `useUpHeat`), heat cleared every tick, sources beside/above ignored, `powerBuffer = (long)(heat * 0.5)`, `getPower() == getMaxPower()`, no cog -> no `tryProvide`, no heat and a 1 HE/t buffer decay.
2. Gear installation through `tryInstallGear`: plain gear consumed and saved at once; engine with a cog, wrong item and META 1 gear refused; overspeed and cooldown reset without a cog.
3. Overspeed at 301 TU/t: warning on tick 61 (volume 2.0, pitch 1.0 above the core), 100 tick cooldown, destruction on tick 301 (explosion strength 5 without fire or block damage, one cog) for all four facings with the original launch direction and speed; 300 TU resets the count.
4. Firebox pairing, firebox ticked before the engine: coal cold start never overspeeds, pre-filled 44 overspeed ticks without warning, 100 HE/t; 300 TU/t cold start pulls exactly 300 TU, pre-filled 93 overspeed ticks with one warning, 150 HE/t; 500 and 1500 TU/t destroy the cog on ticks 309 and 303 cold, 301 pre-filled.
5. Connections: x+-2/z+-2 facing outwards for every facing; direct provision reaches all four points every tick; four separate cables all get the engine as provider every tick; a coal-heated engine delivers 100 HE/t into a battery socket through a cable on each side; nothing without a cog.
6. Save and sync: `powerBuffer`, `hasCog`, `overspeed` saved, `heat` and `warnCooldown` not; sync every tick with range 150; `serialize`/`deserialize` round trip; the client spin (25 degrees per tick at 150 HE, wrapping at 360).
7. Items and anvil recipes: the last five construction entries (two constructions, recycling with and without gear, gear recycling) with their inputs, META rules, outputs, tiers and overlays; all outputs plain and stackable with plain gears and engines.
8. Stray cog: 1000 rubble damage, giblets payload (cDiv 5) and wooden-door sound only for killed living targets; slow top-face hits lie down on the hit point, slow side-face hits only stop; fast hits bounce, explode (strength 3, no block damage) and remove blocks below resistance 50; first-tick hits ignored; lying cogs stay until their block changes, also after a reload; pickup gives a plain (or META 1) gear; NBT `rot`/`meta`/`inGround`/`xTile`...
9. Whole chain: coal firebox -> engine -> two cables -> battery socket for 1,200 ticks, with the engine output equal to half the removed heat and to the socket's gain every tick; then save/load of all three and 20 ticks of the reloaded chain at 100 HE/t.

## Not covered

- `MachineStirlingBlock` (not compiled, see above): the `UPGRADE_PLUG` install sound (volume 1.5, pitch 0.75) and the sneak/wrong-item pass-through of `useItemOn`, the gearless state after placing a META 1 item (`setPlacedBy`), the application of `getDropMeta()` in `getDrops` including the core lookup for explosions (the block-entity method itself is checked in section 7), a single drop per player break, the four `makeExtra` parts being power proxies, and the look overlay. The block-entity side of each (`tryInstallGear`, `hasCog`, save keys) is covered.
- The 300 and 500 TU/t fuels are synthetic items whose registry paths contain `solid_fuel` and `rocket`, so they take the real `ModuleBurnTime` rules; the burn times of NEO's `SOLID_FUEL`/`ROCKET_FUEL` items and whether they are obtainable are not checked. The 1500 TU/t rows set the firebox's public `burnHeat`/`burnTime` directly, because the balefire multiplier only applies to `NtmItems.BALEFIRE_AND_STEEL`, which has no burn time in the stand-ins.
- The destruction ticks depend on the tick order. The regression ticks the firebox before the engine (309/303 cold); an engine-first order would give 310/304 by the same formulas, which is not run.
- Real ray tracing, collisions, drag, the vanilla damage pipeline, death and giblet rendering, explosion effects, NeoForge registries, network packets, entity/block-entity rendering, item tags, dedicated servers and gameplay. PowerNet's 3 s wall-clock timeouts do not come into play in these runs.
