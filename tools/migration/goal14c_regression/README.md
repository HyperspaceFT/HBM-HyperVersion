# Goal14C isolated production regression

Run from NEO with the existing Python/JDK21/cache:

```powershell
python -B -X utf8 tools/migration/verify_goal14c.py
```

`--world machine|recipe|all` selects coverage. Each invocation creates a new
`build/migration/goal14c/regression/<UUID>`; it never replaces earlier output.
The runner uses javac/java, real cached Gson and NeoForge source declarations.
There is no Gradle, game, service, download, installation or real config write.
`result.log` records exact commands/errors; `summary.json` records every compiled
production source SHA256 and requires those files unchanged during the check.

The recipe world compiles complete production SerializableRecipe/GenericRecipes/
GenericRecipe, inherited 13B/14B tables and the compressor table, snapshot,
client helper and packet. It checks normal `ass.compressor` in both 528 modes:
8 steel cast plates with production enum META, 4 copper plates, 2 steel shells,
3 motors and 1 analog circuit, 200 ticks/100 HE, no blueprint pool or duplicate.
`assembly-reference-528-false.json`, `assembly-reference-528-true.json` and
`_hbmCompressor.json` come from actual production writers. Existing
`chem.deshcracked` is checked exactly once with unchanged values.

The five defaults and exact duration/amount/pressure template roundtrip are
checked independently. Custom duration, old missing-duration 100, enabled empty
table, invalid integers/types/pressures/quantities/fluids, valid zero output,
overcapacity values, duplicate keys, 4097 rows and malformed late rows are
covered. Direct `readRecipeStream` and client snapshot replacement are atomic.
The legacy `SerializableRecipe.initialize` still deletes the existing table
before reading an enabled custom file: an invalid enabled disk file throws and
leaves its special table empty. That path is tested and is not a previous-table
fallback. Legacy receive/clear public bridges are exercised; no production
callers were found outside their declaration during this implementation.
The actual compressor packet uses independent client snapshots; integration
server table isolation, immutable records/map, authoritative empty snapshots,
UTF8 bound, early/late refresh callback, reconnect/disconnect and targeted sync
dispatch are checked. Transport/event/JEI callback services remain stand-ins.

The machine world compiles the whole production compressor BE/menu/table,
UpgradeManagerNT, 14A diesel/menu/control, chemical plant/module, actual
FluidTank/transceivers, PowerNetMK2/FluidNetMK2, pipes/cables/storage, and the
inherited machine sources. Compressor logic and storage/network algorithms are
not reimplemented. It checks strict power >2500, no early material mutation,
completion, all five special outputs plus generic pressure0..4, enabled empty
table generic behavior, insufficient input, exact output capacity, full/overcap/
integer overflow, progress reset/restoration, four filtered slots/Shift/side
automation, exact C2S tag/type/menu/distance/level/core identity and one effective
callback despite the shared dispatcher calling both overloads. NBT and buffer
roundtrip, dirty-gated saves, clear-on-identity versus same-identity retention,
and real pipe/cable subscription/removal/resubscribe are covered.
The network menu constructor is checked from manually supplied dummy/EXTRA links
in four facings through production CompatExternal and source-extracted
DummyableBlock.findCore. This is a constructor/core-resolution check; physical
placement, full compressor block construction/refund/removal belong to the
parent's separate structure suite.

Upgrade tests use all 100 ordered pairs of empty or production-registered
SPEED/POWER/OVERDRIVE tier1..3 items in the two actual upgrade slots. They cover
manager caps, caching, generic discrete delays, special sequential divisions,
integer energy floors and a short custom recipe's minimum1 tick. The API accepts
OVERDRIVE cap9, but the existing registry/two slots reaches at most6; the suite
does not pretend all three upgrade types or tier9 are simultaneously equipable.
Two separately labelled SYNTHETIC manager/API boundary scenarios inject a
single OVERDRIVE tier9 and tier10 using the same identity: the manager returns9
in each case, and generic compression takes10 ticks at47500 HE/t. These test
the declared cap9 and >9 clamp without claiming registered or survival tiers.
Registry identities/type+tiers are stand-ins built from production declarations;
full item tooltip/registry boot is not executed.

Finite scenarios explicitly inject starting resources and never assign power
per tick. Sources are 14A final production fuel initialization/calculation bodies
extracted into the service Fluids registry, extended with the actual final LPG
registration call (3397 HE/mB). These extraction assertions/services do not prove
full production Fluids initialization. Independent scenario counters exclude
the separately reported repeated per-tick assertions.

- `supply-accounting.json`: 120 mB single gasoline/diesel engines cannot finish
  a 100 tick generic batch and progress resets. Three gasoline engines with
  100 mB each produce 339600 HE, consume 250000 HE in a complete default batch,
  retain 89600 HE and discard0.
- `desh-accounting.json`: 1000 mB injected LIGHTOIL_CRACK is compressed at2500
  HE/t with three finite gasoline engines and transferred by actual FluidNet
  pressure1 into actual `chem.deshcracked`. Two mixtures +200 mB Hg produce
  exactly2 Desh in200 chemical ticks. Initial chemical25000 + generated339600
  equals compressor250000 + chemical20000 + final94600, with no discarded HE.
- `lpg-single-batch-accounting.json`: exactly2000 mB petroleum0 ->2000 mB
  petroleum1 ->1000 mB LPG0, two actual20 tick compressors consume100000 HE.
- `lpg-accounting.json`: two finite batches (4000 petroleum0) create a real
  overlap where both default compressors consume5000 HE/t. Five engines with
  finite gasoline supply actual PowerNet; 300 of the starting400 mB are burned.
  Compressor cost200000 HE, startup gross339600 HE, transferred4000 petroleum1,
  resulting2000 LPG0. Actual FluidNet hands LPG to a real14A diesel generator;
  actual PowerNet sends600000 HE to an actual battery socket. LPG gross6794000,
  total discarded6144000 and final buffers789600 close the account. Generator
  clipping is measured; battery capacity is respected and fuel is finite.

For finite chain transfer graphs, the fixture registers real endpoints directly
with actual network objects, choosing tick ordering and topology. Separate
lifecycle checks create real pipe/cable nodes and let production getConPos/
trySubscribe perform membership. These are complementary evidence; finite chain
results do not prove physical routing or Minecraft scheduling. Upstream oil
extraction/heating/refining/cracking/fractionation is not rerun in this suite.

Inherited fixture substitutions: Minecraft Level/players/registry boot, ItemStack
components, NBT objects, byte buffers, packet/event queues, sound and rendering
are isolated services; FluidType internal-name lookup reflects service registry
fields. Library battery charge/discharge bodies and final fuel calculations are
source-extracted production methods. DummyableBlock services carry selected
production bodies. The unrelated AnvilRecipes generated copy removes only the
historical Goal13A additions using the existing read-only adapter. The machine
world's SerializableRecipe is an empty boot/JSON service; all loader parsing is
tested in the complete recipe world. Exact generated sources are retained.

A pass establishes isolated source behavior only. It does not establish a mod
build/JAR, actual gameplay/UI/JEI, saves/chunk reload, multiplayer, dedicated
server or third-party integration acceptance.
