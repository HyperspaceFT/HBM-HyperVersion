# Goal 3C isolated assembler and energy integration regression

From the NEO repository root, run with the existing Python and Java 21:

```powershell
& 'C:\Users\显卡超频和烤机测试\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B tools/migration/verify_goal3c_processing.py
```

Each run creates Java stand-ins, compiled classes, and `result.log` in a fresh UUID directory under `build/migration/goal3c/processing-regression/`. The compile includes **unchanged production** `AssemblyMachineRecipes`, `ModuleMachineBase`, `ModuleMachineAssembler`, `MachineAssemblyMachineBlockEntity`, `MachineWoodBurnerBlockEntity`, `ModuleBurnTime`, the energy interfaces, `PowerNetMK2`, `Nodespace`, `UniNodespace`, cables, and proxies. The integration assertion invokes the actual burner tick, actual network update, actual assembler tick, and actual processing module until one shredder is made. It disconnects and restores a production cable during a partial cycle.

`AssemblyMachineRecipes.registerDefaults()` executes the real production registration. Its `ass.shredder` name, 100-tick duration, 100 HE/t requirement, three input slots, plate tag requirements, motor count, and output are asserted from the resulting recipe object. `GenericRecipe`, `GenericRecipes`, `RecipesCommon`, `MetaHelper`, Minecraft items/tags/components, menus, fluid tanks, batteries, sounds, and other surrounding services are narrow stand-ins; the registration data is real, but the loader, tag registry, and JSON override path are not. A second item added to each modeled plate tag checks acceptance by the module under that contract; this does not establish compatibility with an installed third-party mod.

Menu identity and `stillValid` results are modeled so the production permission and selection methods can be exercised. The harness does not compile the real menu, dispatch a packet, launch Minecraft, create a world, or validate JEI transfer. Fluid IO and battery charging are inert stand-ins. The integrated case verifies energy transfer and processing with an isolated test world model; it does not establish in-game client, server, or save compatibility.

The placement checks call production `MachineAssemblyMachineBlockEntity.canPlaceItem` with a modeled `IBatteryItem` marker and recipe ingredients. A first-accepted-slot probe uses the menu's documented machine-slot order to show which slot the machine contract would accept first. It does **not** execute `MenuBase.quickMoveStack`, `SlotNonRetarded`, or the actual menu engine.

The pooled-recipe guard uses one explicitly registered **test fixture** recipe and a blueprint stand-in after the real defaults have loaded. It tests the production selection and module checks, not a claim that `fixture.pooled` is a shipped recipe. The NBT and sync assertions cover production assembler power, module selection/progress, and stub tank state. `MachineBaseBlockEntity` is a stand-in here, so base inventory save/load is **not** covered.
