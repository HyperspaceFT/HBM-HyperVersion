# Goal 3B isolated wood burner regression

Run from the NEO repository root with the existing bundled Python and Java 21:

```powershell
& 'C:\Users\显卡超频和烤机测试\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B tools/migration/verify_goal3b_generator.py
```

Each run writes stand-ins, compiled classes, and `result.log` in a fresh UUID directory under `build/migration/goal3b/generator-regression/`. The script compiles **unchanged production** `MachineWoodBurnerBlockEntity` and `ModuleBurnTime`; Java assertions invoke their actual burn, inventory, control, save/load, and sync methods.

Minecraft blocks/items, furnace burn values, tags, player/menu identity, fluid and energy neighbors, battery charging, and pollution are small stand-ins. They are only contracts for the method calls under test. The menu stand-in carries `be` identity but this harness does not compile `MachineWoodBurnerMenu`, validate slot movement or packets, or prove multiplayer authorization. Its validity flag represents the result of Minecraft's `Container.stillValidBlockEntity`; it does not run world-distance or chunk-lifecycle code. Fuel burn values in the stand-ins are 300 ticks for oak logs/wood/planks, 100 for saplings, 1600 for coal/charcoal, and 20000 for lava buckets, matching the expected vanilla furnace values at this target version. Oak wood is modeled as a member of `ItemTags.LOGS`, so it receives the 4× log multiplier; planks receive the 2× wood multiplier. This harness verifies the production multiplier and machine logic given those values, not the game registry. Liquid fuel, battery charging, network transfer, pollution integration, rendering, and gameplay are not end-to-end tests here.
