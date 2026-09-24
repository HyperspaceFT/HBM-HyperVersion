# Goal 6 isolated storage and liquid-power regression

Run `python -B tools/migration/verify_goal6.py` with the existing Python and JDK 21. Each run writes its commands, compiler output and assertions to a distinct `build/migration/goal6/regression/<id>/result.log`. The script refuses to run if any stand-in would shadow a production source.

## Production code under test

The script compiles and executes unmodified production code:

- **Batteries and the socket:** `IBatteryItem`, `BatteryPackItem`, `BatteryBaseBlockEntity`, `BatterySocketBlockEntity`, `BatterySocketMenu`, `IOrderedEnum` and `EnumUtil`.
- **Energy network (the Goal 3B set):** `ProxyComboBlockEntity`, the MK2 energy interfaces, `PowerNetMK2`, `UniNodespace`/`NodeNet`, and cables.
- **Machines:** the wood burner, `MachineShredderBlockEntity` and its menu.
- **Goal 5C container chain:** the heater firebox, combination oven and recipe, `FluidTank`, `FluidContainerRegistry`, the standard loader, `MetaHelper` and `FluidIDMultiItem`.

The assembler is excluded because this chain does not reach it.

## Stand-ins

`goal6_regression/stubs.py` starts from the Goal 5C stand-ins. It removes the Goal 5C stubs for `IEnergyProviderMK2`, `IBatteryItem`, `ILoadedBE` and `BatteryPackItem`, so the production versions compile instead. It then models the following:

- **World:** `Level` with a manual clock, a set of powered positions for `hasNeighborSignal`, and block entity lookup.
- **Menus:** `Container.stillValidBlockEntity` checks the current block entity and a per-player reach flag.
- **Data:** item registry IDs, the item stack component map, NBT, and the byte buffer.
- **Pollution:** `PollutionHandler` only records soot calls. `SOOT_PER_SECOND` is the production expression, extracted from the source.
- **Fluid traits:** `FT_Flammable` values for `COALCREOSOTE` and `WOODOIL` are taken from the `registerCalculatedFuel` literals in `Fluids.java`, with a check that its rounding is the identity for them.

## Not covered

- Config overrides from `hbmFluidTraits.json`, `Fluids.initialize()` and registry loading are not executed.
- `Library.chargeItemsFromTE` and `Library.chargeTEFromItems` are inert, so machine battery slots are outside this result.
- Chunk unload is modeled through `isLoaded`, `setRemoved` and removal from the level; the real NeoForge unload events are not fired.
- Save and load call the production `saveAdditional`/`loadAdditional`. The wood burner uses `Goal6MachineAccess` because those methods are protected. Disk codecs are not exercised.
- Control packets call the production `receiveControl`/`hasPermission` through a modeled `CompoundTagControl` handler; nothing is received from a real network.
- Client screens, rendering, real inventories, gameplay, multiplayer and dedicated-server loading are untested.

## Sections

1. Pack values, META and `Charge` storage.
2. Socket rates, capacity, redstone and control modes, priority, and save marking.
3. Automation extraction by mode, including EXTRA proxies.
4. Network roles and conduction while disabled.
5. Charge and discharge limits with two priority levels.
6. A three-priority characterization of the inherited upstream `PowerNetMK2` shortfall. This asserts current behavior; it is not a fix.
7. Unload pruning, removal, save/load, node rebuild and GUI sync.
8. Menu Shift rules and control permission.
9. Proxy direct-provision parity.
10. Wood burner liquid boundaries: 250 HE/t for creosote, 125,000 HE per 1000 mB, soot, near-full clamp, wood oil, water, and save/load.
11. The integrated chain, starting from an uncharged firebox and oven:
    - ten coal produce ten coke and 1000 mB of creosote, which fill a universal tank;
    - an identifier selects the burner's fluid, and the burner unloads the tank and burns it in liquid mode;
    - energy is checked for conservation every tick across burner, cables, socket and shredder;
    - the socket then discharges through redstone;
    - a cable is removed and replaced, and supply resumes at the 100 HE/t pack limit.

`build/migration/goal6/mutation_check.py` reverts each of the six Goal 6 production fixes in a temporary copy and confirms that this regression fails on each one.
