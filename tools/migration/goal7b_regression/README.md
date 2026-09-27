# Goal 7B isolated fluid logistics regression

Run `python -B tools/migration/verify_goal7b.py` with the existing Python and JDK 21. The script finds the JDK through `JAVA_HOME`, then `C:\Program Files\Java\jdk-21`, then the `PATH`. Each run writes its commands, compiler output and assertions to a distinct `build/migration/goal7b/regression/<id>/result.log`, and refuses to run if any stand-in would shadow a production source.

`python -B tools/migration/goal7b_mutation_check.py` reverts each of the eight Goal 7B production changes in a temporary copy of `src/main/java` and confirms that the regression fails on every one (log: `build/migration/goal7b/mutation_check.log`).

## Production code under test

Everything the Goal 6 regression compiles (energy network, battery socket, wood burner, shredder, firebox, combination oven, `FluidTank`, container registry and loaders), plus the production fluid network that Goal 5C/6 had replaced with inert interfaces:

- `FluidNetMK2`, `FluidNode`, `FluidNetProvider` and the `IFluid*MK2` interfaces (connector, pipe, provider, receiver, standard sender/receiver/transceiver, user);
- `PipeBaseBlockEntity`;
- `BarrelBlockEntity`.

## Stand-ins

`goal7b_regression/stubs.py` starts from the Goal 6 stand-ins and then:

- removes the inert fluid interfaces and the no-op `trySubscribe`/`tryProvide` on the `LoadedBaseBlockEntity` stand-in, so the production defaults run;
- gives `FluidType` the production `FluidNetProvider` and plain hot/corrosive/antimatter flags;
- models blocks as identities (`BarrelBlock` carries only its capacity);
- records `destroyBlock`, `explode` and comparator neighbour updates on the level instead of simulating them;
- stubs the barrel menu, the duct block's recursive retyping and the player key attachment used only by the copy tool.

The older Goal 3B/5A/5C stand-ins only gained inert declarations (`Direction.Plane`, default `transferFluid`/`useUpFluid`) so they still compile the changed production classes; their assertions are unchanged.

## Not covered

- NeoForge registry loading, real chunk unload events, disk codecs, network packets, client rendering, the duct block's visual connection state and dedicated servers.
- `NodeNet` subscription timestamps use `System.currentTimeMillis()`; section 7 therefore sleeps 3.1 s of real time.
- The duct block's `useItemOn`/`changeTypeRecursively` and the barrel menu are not executed; pipes are retyped through `setFluidType`.

## Sections

1. Pipe network: 10,000 mB through five pipes, a water pipe splitting a creosote line, retyping back, removing and replacing a pipe, pipe `Type` save/load, and a creosote barrel refusing a water line.
2. Barrel roles in all four modes, mode cycling with save marking, NORMAL-before-LOW priority, a buffer barrel joining two pipe runs, and an input barrel ending a line.
3. Barrel save marking for container load/unload and for network drain, comparator updates, save/load and the dropped item's contents.
4. Safe/steel barrel hazards with hot, corrosive and antimatter fluids (mechanism only).
5. Combination oven: the 24-point connection shape, an upper-layer corner-side pipe draining the oven, drain save marking with no fluid duplication on reload, and the 20-tick provider registration.
6. Wood burner: both fluid ports face backwards for all four facings, the core accepts pipes only from the back, and piped fills of an idle burner are saved.
7. Characterization of the inherited 3 s wall-clock subscription timeout.
8. Integrated chain: 10 coal in a firebox-heated oven → pipes → buffer barrel → pipes → a nearly full burner, with fluid conserved every tick; then 200 burning ticks refilled from the buffer, and save/load of all three machines.
