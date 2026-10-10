# Goal14A isolated diesel and gasoline-chain regression

Run `python -B -X utf8 tools/migration/verify_goal14a.py`, then
`python -B -X utf8 tools/migration/goal14a_mutation_check.py` from NEO.
The existing JDK21, Gson and NeoForge sources cache are required; nothing is
downloaded or installed. `--world machine|recipe` selects the relevant world.
All ordinary generated sources, classes, logs, recipes and accounting JSON stay
under a new `build/migration/goal14a/` run directory. The mutation checker makes
source copies there, requires an unmutated pass, and accepts only the intended
Java AssertionError; a compile failure is not mutation detection.

The recipe world compiles actual SerializableRecipe, GenericRecipes,
GenericRecipe, assembly and chemical tables through the existing Goal13B recipe
world. It compares every old assembly entry, relative order and blueprint pool
against the frozen `006f71f1` copy provided by the parent in
`baseline-files/src/main/java/com/hbm/inventory/recipes/AssemblyMachineRecipes.java`.
The run checks its SHA256 against the parent's baseline.json before compiling.
Both 528 modes are covered. The actual loader checks missing custom files,
template round-trip and replacement tables which omit/include diesel. The
actual writer emits `ass.dieselgen.recipe.json` and `chem.gasoline.recipe.json`.
Registry IDs and tags remain fixture services, as in earlier recipe worlds.

The machine world compiles the current production MachineDieselBlockEntity,
MachineDieselMenu and CompoundTagControl unchanged, plus the existing Goal13A
production machines, MachineBase, menus, battery item/socket, cable and pipe
nodes, power/fluid networks, chemical module/recipes, tank and standard container
loader. Its complete production list appears in result.log. The unrelated anvil
entries use the historical Goal13A compatibility adapter only. The diesel block
and client/resource classes are not compiled here; the main wrapper and resource
checks cover those separately.

Source-extracted methods are disclosed: Library.chargeItemsFromTE is copied
verbatim from the current production source into the inherited Library service;
the final Fluids.init numeric constants and six registerCalculatedFuel calls,
registerCalculatedFuel and round bodies are compiled in the fluid registry
service. The round helper is renamed locally to avoid the inherited flammable
helper name. This exercises the actual derived calculation, not complete
Fluids.init registry/config boot. FT_Combustible is the unchanged production
class. Independent expected final values are naphtha165000, gasoline1510000,
diesel1370000, kerosene3850000 HE/bucket, yielding82/1132/1027/385 HE/mB under
the original division-before-efficiency rule. A non-integral bucket value and
trait replacement ensure the generator follows current traits rather than the
early fluid literals or duplicated arithmetic.

Minecraft Level, player, container services, item registry/components, NBT
objects and byte buffers are inherited isolated models; slots additionally
retain their GUI coordinates, and typed NBT checks model boolean-byte/long tags.
The actual packet handler executes through an immediate IPayloadContext queue;
transport codec buffers are services. Rendering, sound playback, packet transport,
real thread scheduling, chunk IO, save files, datapack/tag binding and other mods
are not established by this harness. No real gameplay, UI, multiplayer or
dedicated-server claims follow from passing checks.

The chain starts with one explicit10000HE injection and1000mB naphtha. The real
chemical plant costs4000HE and produces800mB gasoline, transported by real pipe
network nodes to diesel. Eight hundred actual burns generate905600HE gross;
finite generator/socket capacity clips some of it. Stored HE, generator buffer,
clipped loss and an actual chemical load's4000HE processing cost are accounted
separately in chain-accounting.json. The fixture chooses tick order and node
passes; it never refills plant power each processing tick. The load's network
buffer fill can delay processing, so the fixture bounds convergence separately
from asserted processing HE. This is a bounded naphtha-to-load chain, not the
earlier oil extraction/refinery chain's energy accounting.

The second chemical load receives an independently supplied1000mB naphtha.
Its800mB gasoline output remains in that load and is not recycled/burned in this
run; JSON records both material injections and this remaining output. The initial
plant's6000HE remainder is retained too. The closed final assertion is
initial injection + gross generation = remaining initial plant power + initial
fuel processing cost + clipped loss + generator buffer + storage + load buffer
+ load processing cost. It does not claim a free-energy or zero-power bootstrap.
