# Goal 3B isolated network regression

Run `verify_goal3b_network.py` from the NEO repository root with the existing
Python runtime. It uses the existing JDK 21 and writes a per-run transcript under
`build/migration/goal3b/network-regression/`.

The harness compiles the current production energy interfaces, Nodespace,
PowerNetMK2, UniNodespace and its node/provider classes, CableBaseBlockEntity,
ProxyComboBlockEntity, MachineWoodBurnerBlockEntity, ModuleBurnTime, and
MachineAssemblyMachineBlockEntity. The integrated case runs the production wood
burner's `updateEntity()`, connects its actual rear output to production cable
nodes, runs the assembler's `updateEntity()` subscription path, and checks that
generated energy reaches the assembler with the same debit at the burner.

`stubs.py` supplies Minecraft classes and peripheral services needed to compile
outside NeoForge. In particular, LoadedBaseBlockEntity, MachineBaseBlockEntity,
and ProxyBaseBlockEntity are substitutes for unrelated entity plumbing; their
loading flags, dirty counters, level access, and proxy core lookup are simulated.
Energy transfer interfaces, node topology, network accounting, cable lifecycle,
proxy power delegation, and both machine classes above use production source.
The synthetic `Supply` block entity in NetworkRegression exercises controlled
capacity, branching, disconnect, and provider-unload cases; it does not replace
the real wood burner in the integrated case.

This check does not start Minecraft or NeoForge, dispatch real level events,
load or unload actual chunks, save and reload a world, or exercise a client or
dedicated server. It calls `setRemoved()`, toggles simulated `isLoaded` flags,
and invokes `UniNodespace.removeLevel()` and cache cleanup directly. Its result
supports the compiled network paths and assertions, not in-game acceptance.
