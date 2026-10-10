# Goal15A isolated production regression

Run from NEO with the existing cached Python and JDK21:

```powershell
& 'C:/Users/显卡超频和烤机测试/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -B -X utf8 tools/migration/verify_goal15a.py
& 'C:/Users/显卡超频和烤机测试/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -B -X utf8 tools/migration/verify_goal15a_structures.py
& 'C:/Users/显卡超频和烤机测试/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -B -X utf8 tools/migration/verify_goal15a_affected.py
```

The first runner accepts `--world machine|recipe|all`. Every invocation creates a
new UUID under `build/migration/goal15a/regression`, `structures`, or `affected`.
There is no Gradle, game, server, service, download, install or real config write.
Old verification sources are imported/read unchanged. Exact javac/java commands,
errors, generated sources and source hashes remain in each invocation. The
machine/recipe runner refuses production-service shadowing, hashes compiled and
selected extracted production inputs before/after, and records fixture/service
and cached-library hashes. The structure runner records stable production hashes,
fixture/cache hashes and every command. Earlier failure directories remain.

## Machine world

The new engine BE, engine menu and PistonSetItem are complete production classes.
Complete compressor, diesel, battery socket, arc welder, arc furnace, electrode,
recipe, FluidTank, PowerNetMK2 and FluidNetMK2 logic executes against inherited
Minecraft services. No combustion algorithm or load is replaced. The engine
fixture inherits existing 14C setup/network/accounting helpers but does not run
the old fixture's main or claim its old scenarios as new coverage.

Coverage includes the initial five-slot/24000mB/2500000HE contract, all fifteen
tier/grade efficiencies, actual gasoline/diesel/LPG outputs for all three tiers,
all tenth0..9 and setting0/1/30 tail boundaries, fractional truncation, absent or
invalid piston identity/META, zero efficiency and noncombustible fuel, stopped
state, and absence of the diesel redstone gate. A full-cache case distinguishes
generation -> battery charging -> final clipping from premature clipping. A
zero-cache case proves that the same tick's generated energy charges the battery.

One **SYNTHETIC direct-generate** case starts power at 9007199254740993, above
the machine's normal maximum, and invokes the actual production `generate()`.
It establishes Java's original whole-long-plus-double compound conversion;
it is not a valid loaded machine state or a gameplay capacity claim. The fifteen
grade cases use a synthetic WATER combustion trait with 10000HE/bucket so grade
selection can be checked independently. Residue cases use12345HE/bucket. Actual
gasoline/diesel/LPG cases use source-extracted final production registrations.
The full production Fluids registry initialization is not executed.

Control tests use the actual shared C2S dispatcher and production permission
checks: absent/wrong menu, distance, cross-world, replaced BE, client authority,
null/unknown/multi-action tags, wrong NBT types, valid throttle0/1/30, rejected
false toggle and exactly one effective player callback. Copy settings use the
same current-menu authority; same type retains residue, actual retype clears it,
and invalid throttle rejects the entire retype operation.

NBT/sync roundtrips preserve tenths, fuel, power/settings and open state where
applicable. Corrupt NBT mutates the actual `tank` fill key, forces exact recovery
to0/24000 and verifies setting0/30, tenth0/9, power0/2500000, capacity24000 and
pressure0. Idle pipe fill and external power debit mark dirty; a dirty-gated
save/restore executes actual NBT methods. Identifier/type changes remove stale
fluid membership; actual pipe/cable subscription, unload and removal cleanups
are covered. Container loading exercises complete production transfer logic,
full/incompatible output refusal and insufficient24000mB capacity. Manual/Shift
filters and battery/piston components are checked; original sided automation is
empty. Four facings of manually linked DUMMY/EXTRA positions exercise the actual
menu buffer constructor and CompatExternal/core resolution, including open/close
counts. Physical placement is covered separately below.

Finite scenarios never assign HE per tick:

* `wire-gate-accounting.json`: one/two/three actual LPG diesel generators, each
  starting1100mB, feed the actual welder through PowerNet. An initial unpowered
  welder tick obtains its production recipe-dependent capacity. Three generators
  burn2400mB over800ticks, generate8152800HE, consume8000000HE to make8gold dense
  wires META7900, discard0 and retain152800HE. One/two generators cannot keep
 10000HE/t progress continuous and produce0wires in the same interval.
* `furnace-accounting.json`: engine buffer and furnace buffer both start0HE,
  engine fuel starts600mB LPG. Actual SPEED2/3 upgrades, valid FLINT recipe and
  three source-declared graphite electrodes drive the real furnace. Over81ticks,
  Desh25k advances every tick and actually converts material/wears electrodes;
  Dura24462 has2undersupplied ticks. At125k Dura/Desh have66/64undersupplied ticks.
  Output/processing is finite evidence, not indefinite survival-chain proof.
* `lpg-engine-accounting.json`: five diesel starters receive40mB gasoline each,
  and two actual compressors receive2000mB petroleum0. Production methods and
  actual FluidNet make1000mB LPG0 at100000HE compression cost and send it into
  Desh engine. Its167ticks burn all10000tenths, including the40tenth final tail,
  generate4530000HE, and transfer167000HE to a real battery socket. Explicit
  clipping and all machine buffers close the whole startup/processing/generation
  account. Upstream extraction/refining/cracking/fractionation is not rerun.

For finite chain graphs the fixture registers actual endpoints directly with
real network objects and selects tick ordering/topology. Separate pipe/cable
tests execute production subscription methods. Neither establishes physical
Minecraft routing or its scheduling.

Independent scenario counters are separate from repeated per-tick assertions.
The final stdout reports both; its total includes repeated assertions. A tick
assertion does not count as another independent scenario.

## Recipe world

Complete production AssemblyMachineRecipes, GenericRecipes/GenericRecipe,
SerializableRecipe and inherited recipe tables/writers compile against services.
The frozen `goal15a/baseline-files` assembly source must match baseline.json's
hash and is compiled in a separate package. Both528settings require exactly four
new rows and retain every previous recipe's writer contents and relative order.
All quantities, time/HE, no blueprint pool, correct integrated board, tag inputs,
wire META7900, tungsten bolt META7400, Dura bolt META33 and piston META0/1/2 are
checked. Correct-component quantity negatives and wrong-material positives use
source-extracted production ComparableStack.matchesRecipe. Writer/reader roundtrips execute production
methods after deleting the existing table so duplicate IDs are not silently
overwritten. `goal15a-assembly-recipes.json` exports the actual four production
rows for the parent's migration record.

Recipe-world piston/bolt/wire declarations are source-extracted enum services;
full piston behavior executes in the machine world. ItemStack META, item/tag
registry boot and tag membership are services, so this is not registry/datapack
or survival-acquisition acceptance. The empty-canister fluent datagen statement
is checked statically for shape/material/output/count and hashed. Generation and
generated/packaged recipe checking belong to the parent's resource workflow.
Both-mode registration of the new four rows does not make the existing gated
microchip manufacturing path available in528mode. Existing gates remain intact.

## Structure world and affected historical checks

Actual DummyableBlock, MultiblockHandlerXR, engine geometry/placement/port/proxy,
ownership and teardown method bodies execute in an engine-service world. The
independent expected footprint is24cells in four facings. Every non-core cell is
blocked in turn; refund keeps the original at-limit stack and custom component.
Core/dummy/EXTRA direct and player teardown cases retain a touching neighboring
engine. Core/ordinary/EXTRA non-air replacements survive; a foreign same-identity
core inside the box remains. Creative/client placement boundaries are checked.
The cached Minecraft BlockItem source establishes consume-after-callback order.
Five compiled behavior mutations remove an upper layer/EXTRA ports, lose refund
components, over-broaden ownership or remove replacement protection. Each must
compile successfully and fail a behavior AssertionError.

The inherited generated structure template contains unrelated fraction/compressor
shells, but only the new Engine shell is exercised by this fixture. Engine world
services model state publication and old-state onRemove callbacks; they do not
launch Minecraft or reproduce its full block/loot/neighbour engine.

The affected runner replays14A,14B,14C,G11D,fluid-save and lifecycle suites. It
copies/adapts output-boundary strings and exact old14A delta anchors to acknowledge
diesel+compressor+four15Arows, preserving all old recipe content/order assertions.
It adds source-derived piston/bolt/wire enum declarations and previous14B/14C
handler names/writer-call additions. These small declaration adapters do not
verify new logic; new logic belongs to the Goal15A worlds. Original historical
scripts/Java fixtures and production files are hashed and must remain unchanged.

Minecraft Level/player/registry boot, ItemStack components, NBT/buffer storage,
sound/render/packet/event transport, unrelated JSON boot in the machine world,
and load-only menus for arc furnace/welder remain isolated services. Library
charge/discharge and selected fuel/registry/component/core-resolution bodies are
source-extracted production methods. The inherited unrelated AnvilRecipes copy
uses the existing read-only Goal13A adapter. Exact generated services remain in
the output for review. A pass establishes isolated source behavior only; it does
not establish a mod build/JAR, game/UI/JEI, real saves/chunk reload, multiplayer,
dedicated server or optional-mod acceptance.
