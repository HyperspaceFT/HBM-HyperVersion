# Goal 3a isolated recipe and machine regression

Run from the NEO repository root with the existing bundled Python and JDK 21:

```powershell
& 'C:\Users\显卡超频和烤机测试\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B tools/migration/verify_goal3a.py
```

Each run writes Java stand-ins, compiled classes, and a `result.log` under a new UUID directory in `build/migration/goal3a/regression/`. The script compiles the **unmodified production** `PressRecipes`, `BlastFurnaceRecipes`, `BlastFurnaceRecipe`, `MachinePressBlockEntity`, `MachineBlastFurnaceBlockEntity`, `AnvilRecipes`, `AnvilSmithingRecipe`, and `InventoryUtil` classes. Assertions load the real default recipes and execute their production matching and machine/anvil methods. The test does not infer recipes from source text; parsing item names only generates external registry stand-ins needed to compile the anvil class.

The Java stand-ins model only the calls used by these isolated checks. In particular, item identity and metadata, stack counts, fuel, inventory insertion/rejection, drops, and the relevant player/menu notifications are simplified. Minecraft registries, data components, tags, JSON recipe loading, world state, networking, save/load, and actual UI/gameplay remain outside this harness. The anvil uses a narrow `RecipesCommon` and `MetaHelper` stand-in, so its metadata assertions establish that the production registration supplies the expected variants and counts under that contract; they do not validate the full Minecraft component implementation. The full inventory drop path is exercised by making the inventory stand-in reject insertion after a craft; ordinary consumption can free slots in an otherwise full inventory.

The existing Goal 2 harness remains the regression for steel, plates, and inventory/menu behavior:

```powershell
& 'C:\Users\显卡超频和烤机测试\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B tools/migration/verify_goal2.py
& 'C:\Users\显卡超频和烤机测试\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B tools/migration/verify_goal2_menus.py
```

Goal 12A (`migration/GOAL12A.md`, `build/migration/goal12a/production.diff`) names `WireDenseItem.Type.GOLD.meta` in `AnvilRecipes` (the desh motor entry); `anvil_stubs.py` adds a `WireDenseItem` stand-in with the constants the anvil source names and the ordinal as a stand-in meta, so the Goal 3A, 5A acquisition and 5A casting anvil worlds compile again. No assertion changed.
