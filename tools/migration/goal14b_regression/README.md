# Goal14B isolated fraction regression

Run from NEO with existing Python and JDK21:

```
python -B -X utf8 tools/migration/verify_goal14b.py
python -B -X utf8 tools/migration/goal14b_mutation_check.py
```

`--world machine|recipe` selects a world. `--output` stays under
`build/migration/goal14b/regression` or `mutations`; mutation `--source` copies
stay under `mutations`. Generated fixture services, class files, config JSON,
accounting, and logs never write old fixture outputs. Existing Gson and the
NeoForge sources cache are required; no download, Gradle, game or EULA is used.

The machine world compiles the whole current fraction tower and fraction table,
the Goal14A diesel/menu/control classes, and inherited Goal13A production
machines, including the refinery, tanks, transceiver interfaces and network
classes. The complete source list and commands are in each `result.log`.
The historical inherited adapter removes only the Goal13A anvil additions from
the unrelated anvil class in the generated copy. Fraction source is unchanged.
The machine SerializableRecipe service has empty JSON methods; the table's
default registration is exercised here, while all JSON behavior is tested with
the complete production loader in the recipe world.

Machine assertions cover three 4000 mB tanks; 0/99/100 inputs; exact capacities
and either output overflowing; 10 tick processing; recovery; missing recipe
clearing with pressure retained; custom negative/overflow quantities; upward
input/downward products; both entities dirty; type changes and bottom-only
copy gate; absent Y+3 tower (including a spacer-sized Y+4 gap); two/three tower
orders with per-tick conservation and capacity bounds; external transceiver
input/output dirty; and type/amount/pressure NBT and byte-buffer round trips.
The Level manually supplies tick order. It does not establish Minecraft chunk
scheduling, a real spacer's world behavior, real saved data or packet delivery.
Structure/placement/refund assertions belong to the separate block fixture.

The finite chain calls the **actual production refinery `refine` method** by
reflection, rather than its complete update lifecycle. Its starting resources
are 4000 mB hot oil and 1000 HE. Forty batches cost 200 HE and produce 2000 mB
heavy oil, 1000 naphtha, 600 light oil and 400 petroleum. Actual transceiver
receive/debit methods hand those outputs to independent fraction towers; the
fixture chooses transfers rather than constructing a pipe route. Naphtha/light
oil yield 840 mB diesel. Heavy oil yields 1400 smear and 600 bitumen; smear yields
560 lubricant and 840 heating oil. Actual diesel updates burn all 840 mB,
yielding 862680 gross HE, with buffer and clipped loss accounted independently.
The retained material is 600 bitumen, 1240 heating oil, 360 kerosene, 560 lubricant
and 400 petroleum, totaling3160 mB; retained plus burned is4000. Remaining
refinery800 HE + cost200 HE plus generator buffer/clipped loss close against
initial1000 HE + generated862680 HE. `chain-accounting.json` records the account.
Sulfur byproducts are an additional production item output, not part of the
fluid-volume account. No free-energy or full oil extraction/boiler chain claim
follows.

Fuel registry initialization uses the inherited Goal14A source-extracted
production final fuel registration/calculation methods. Minecraft registries,
Level, player, NBT storage and byte buffers are fixture services. The new
FluidType internal-name adapter reflects the service registry fields; it does
not claim full production Fluids boot. No new algorithm is substituted for
fractionate, stack movement, recipe table, NBT or transceiver mutation.

The recipe world compiles unchanged SerializableRecipe, the Goal13B production
tables, FractionRecipes, FractionRecipesPacket, FractionRecipeSync and
FractionRecipeClientSync against real Gson. It asserts all19 original rows
independently, G11D internal names, production template roundtrip, missing/custom/
empty/received replacements, snapshot parsing isolated from the server table,
client stale/empty replacement, malformed and oversized rejection, refresh and
disconnect callbacks, packet UTF8 codec, and relevant-player sync dispatch.
The event and PacketDistributor services record calls; they do not provide a
real event bus, connection, thread queue, JEI refresh implementation or server.
The client snapshot map is tested unmodifiable; mutable nested FluidStacks are
not advertised as deeply immutable. The exported `_hbmFractions.json` is a
production writer reference and can be copied to the migration documentation.

Mutation checks first require an unmodified pass, copy production sources only
under the allowed mutation tree, and accept only the named Java AssertionError.
Compile failures never count. Targeted regressions include second-output space,
10 tick cadence, upper dirty, direction, clearing/pressure, network dirty,
default count, loader clearing and client empty clearing. Whole live Java-source
hashes are compared before/after; run while source writers are idle.

Passing fixture/build/resource evidence does not establish real gameplay,
world saves, UI/Chinese appearance, multiplayer, dedicated-server loading,
rendering, sounds, transport ordering or optional-mod integration.
