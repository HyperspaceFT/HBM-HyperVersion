# Goal15B isolated production verification

Run from NEO using the existing Python, JDK21 and cached Gson/NeoForge sources:

```powershell
& 'C:/Users/显卡超频和烤机测试/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -B -X utf8 tools/migration/verify_goal15b.py
& 'C:/Users/显卡超频和烤机测试/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -B -X utf8 tools/migration/verify_goal15b_structures.py
& 'C:/Users/显卡超频和烤机测试/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -B -X utf8 tools/migration/verify_goal15b_affected.py
& 'C:/Users/显卡超频和烤机测试/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -B -X utf8 tools/migration/goal15b_mutation_check.py
```

Every invocation writes a fresh UUID below `build/migration/goal15b/regression`,
`structures`, `affected` or `mutations`. Failed attempts remain. No original
repository, old verification sources, old release files or real configs are
written. There is no Gradle, download, installation, game, server or EULA action.
The affected runner reads pinned Git history with per-command safe.directory.

## Machine world

Complete current coker BE/menu/table, firebox, AbstractHeaterMachineBlockEntity,
ModuleBurnTime, FractionTower BE/table, FluidTank, FluidNet and inherited machine
classes compile and execute. No coking, heat transfer, fuel multiplier, complete
transaction, progress, NBT, fluid mutation or network algorithm is reimplemented.
The complete compiled source list and javac/java command are in each result.log.
The runner rejects service/production shadowing and records compiled/extracted
production, fixture, generated-service and cache hashes before/after checking.

Independent fixed outcomes cover positive/zero/negative heat difference, upward
rounding, maxHeat short circuit, cooling and clamp loss; heat99/100, completion
and excess progress, one completion per tick, missing input/recipe, blocked
outputs and recipe changes preserving progress. Complete transactions cover
both exact capacities, minimum input, empty slot/full slot, same item with
different modern components, oversized integers, fluid-only/item-only recipes,
old byproduct draining and upstream clear-before-input-check ordering.
Synthetic >100000 source heat and oversized progress are interface/state boundary
tests, not valid loaded firebox or normal survival state claims.

Actual dirty-gated NBT round trips cover both sides of heat transfer, cooling,
partial progress, full completion, byproduct clearing, identifier type change,
idle pipe input/output and output extraction. NBT containers themselves are
memory services, not Minecraft saves. Corrupt loaded heat/progress/fill/capacity
is bounded. Actual synchronization methods preserve machine/tank fields.

The actual menu buffer constructor resolves manually supplied DUMMY/EXTRA links
in four orientations through production CompatExternal and extracted findCore.
Manual filters and sided output extraction are checked. Container's engine
service models entity identity and an inReach flag; this does not execute the
real distance computation. Actual pipe subscription, unload/resubscribe,
identifier retype and remove cleanup execute current production network methods.

The finite chain begins with exactly16000mB BITUMEN, one COKE_COAL item, and
zero heat/progress. The coal-coke burn-time hook is a registry service populated
from the actual NtmItems declaration (3200); actual ModuleBurnTime yields4000
burn ticks and200TU/t. The first ignition tick produces heat without decrementing
burnTime. Firebox heat cap can pause its burn clock; the ledger observes actual
generation, retained heat, cooling, transfer and clamp loss independently.

All machines continue ticking on the same increasing clock after the coking
checkpoint. Actual FluidNet transfers1600mB OIL_COKER into the real fraction
tower;16 actual100mB batches yield480mB CRACKOIL and1120mB HEATINGOIL. The
account records cokingTicks, totalTicks, initial/final world time, checkpoint
and final fuel/heat/progress, processing, cooling and clamp costs. No heat,
fuel or input is refilled per tick. Coal-coke is consumed once; remaining burn
time is retained energy potential, not another intact fuel item. Petroleum
coke and fluid quantities are separate accounts, not a mass-conservation sum.
Tick ordering and endpoint topology are fixture choices, not Minecraft scheduling
or real physical pipe-routing acceptance.

## Recipe world

Complete production SerializableRecipe, assembly and coker tables, snapshot,
client helper, sync and packet run with real cached Gson. All33 defaults are
asserted independently. All25 inputs get final production fuel registration,
registerCalculatedFuel and round bodies extracted in their production order;
fixed expected U and recipe amounts detect initialization/arithmetic changes.
This does not execute full Fluids.init, registry boot or disk readTraits. Direct
custom trait changes test that default coking quantities reflect current traits.

Strict100/1000/10000 boundary neighbors, invalid energy, zero/overflow quantities,
real writer/template/parser/snapshot round trips, complete custom/empty table
replacement, invalid/duplicate/late rows, unsupported pressure, optional outputs
and overcapacity format-legal recipes are covered. Legacy initialize deletes
before enabled invalid disk parsing; it is not a previous-table fallback.

Steel assembly explicitly checks CAST_PLATE_WELDED META11 and rejects iron META0,
four steel shells, eight copper-tag plates, four INGOT_RUBBER and four niobium,
200ticks/100HE, one normal row and retained frozen older table in both528 modes.
Real assembly exports and `_hbmCoker.json` are retained in the recipe output.

ItemStack component maps, registry identities, META and CUSTOM_DATA helpers are
services. The small TagParser service accepts only `{}` or one integer field
such as `{probe:7}`. Actual coker writer/readStrictItem/snapshot code preserves
that CUSTOM_DATA and explicit zero META through the service. This is not evidence
of actual Minecraft SNBT parsing or arbitrary component serialization. Other
unrepresentable components explicitly fail the real writer. Mutable leaf tag
copying is not advertised as deeply immutable.

Client tests cover independent default fallback, authoritative empty/custom
snapshots, malformed/oversized retention, immutable map, server-table isolation,
no-JEI receive, late callback access, disconnect, UTF8 packet bound/codec and
targeted login/reload dispatch. Events/transport queues/callbacks are services;
actual event bus, threads, JEI rendering and optional-mod loading are not run.

## Structures, affected checks and mutations

The structural world extracts actual coker union/placement/proxy/ownership and
teardown bodies plus inherited DummyableBlock methods. An independent union has
307 cells in each facing: tower, wide body and four legs. Every cell resolves its
owner; obstructed cells preserve component-bearing refunds. The clicked cell is
validated by BlockItem before the modeled callback, so obstruction iterations
exclude only that clicked cell. Core obstructions also require exact refunds:
the requirement check runs before placing the true core. Adjacent machines and foreign cores survive
teardown; replacing a cell keeps the replacement block. Cached Minecraft source
establishes callback-before-consume ordering. Placement/rendering/loot still
require real-game evidence. Five compiled structural mutations must fail actual
behavior assertions.

Affected14A/14B/14C/15A/G9A/G11D/fluid-save/lifecycle checks retain all old
assertions. Copied adapters add current handler/enum services, account for the
single coker assembly row, and redirect every generated output. G11D retains
old callers and explicitly adds two coker writer calls. Old source/tool hashes
are checked unchanged. Old fixture-only handler services do not test new coker
behavior; the new recipe world does that.

Eleven coker mutations cover upward rounding, clamp loss, completion count,
progress retention, components, capacity, pipe dirty, heat threshold, byproduct
clearing time, default count and client empty replacement. The unmodified world
must pass first. Each copied mutation must compile and fail its named Java
AssertionError; compile errors never count. Live production hashes must match.

Passing isolation checks do not establish a mod build/JAR, gameplay, Chinese UI,
actual saves/chunk reload, rendering/particles, real JEI, multiplayer, dedicated
server or optional-mod integration. Parent-owned build/package/resource evidence
and later gameplay acceptance remain separate.
