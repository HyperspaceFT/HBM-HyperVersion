# Goal 2 isolated Java regression

Run from the NEO repository root with the existing Python runtime:

```powershell
& 'C:\Users\显卡超频和烤机测试\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B tools/migration/verify_goal2.py
```

The script uses the existing JDK 21 at `C:\Program Files\Java\jdk-21` and writes generated stubs, class files, and a `result.log` transcript in a fresh UUID directory under `build/migration/goal2/regression` for each run. Existing run artifacts remain intact. It compiles the production `MachinePressBlockEntity`, `MachineBlastFurnaceBlockEntity`, and `InventoryUtil` unchanged. Separate compiles use production `PressRecipes`, `BlastFurnaceRecipe`, and `BlastFurnaceRecipes` unchanged. Assertions execute the compiled production methods; no game, Gradle task, network access, or new dependency is involved.

Minecraft, registry, world, fluid network, container, and recipe services use deterministic minimal stubs. The machine fixture's recipe classes are stubs. The production recipe checks use minimal `AStack`, `GenericRecipe`, and `GenericRecipes` services to exercise default registration, selection, quantity matching, and clearing. They do not test JSON loading or the real game registry. Multiplayer sync, GUI, crafting packets, language, block placement, data generation, and in-game behavior remain outside this fixture. Run the repository's normal build/resource checks and, when authorized, game checks separately.
