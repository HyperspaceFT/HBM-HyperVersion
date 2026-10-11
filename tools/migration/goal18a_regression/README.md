# Goal18A isolated verification

These tools reuse the Goal17B machine chain, the Goal16A recipe chain and the Goal17B structure world without modifying the old suites. Run from the NEO repository with the existing Python 3 and JDK 21 (Windows PowerShell or Linux shell; classpaths use the platform separator):

- `python -B -X utf8 tools/migration/verify_goal18a_recipes.py`
- `python -B -X utf8 tools/migration/verify_goal18a_machine.py`
- `python -B -X utf8 tools/migration/verify_goal18a_structures.py`
- `python -B -X utf8 tools/migration/verify_goal18a_resources.py [--source <original worktree>]`

Outputs stay under unique directories in `build/migration/goal18a/{recipes,machine,structures}/`. Every report records source, fixture, adapter, Gson/sources-jar and JDK hashes plus exact commands and exit codes; sources are hashed again after each command. A mutation counts only after successful compilation and an expected behavioral `AssertionError`.

The recipe world compiles the production `CrystallizerRecipes`, `CrystallizerRecipeSync`, `CrystallizerRecipeClientSync`, `CrystallizerRecipesPacket`, `CrystallizerRecipeHandler`, the production loader base and `AssemblyMachineRecipes` (the frozen baseline is the Goal18 planning commit read from git). Item/block registry, tags, components, SNBT and the JEI runtime manager are stand-ins; the real Gson jar is used.

The machine world compiles the complete production `MachineCrystallizerBlockEntity`/`MachineCrystallizerMenu` with the inherited inventory, battery, upgrade, fluid tank/container, power and fluid network production sources. The crystallizer table and client sync are declared services whose rows mirror the independently verified defaults; player attachments are an identity-keyed record so the ladder flag can be read back. The finite ledgers declare a prepared peroxide inventory and a copper capacitor and hand the copper crystal to the real centrifuge over its declared default row.

The structure world extracts the actual geometry, placement, ownership, proxy and teardown bodies; Minecraft registry, world callbacks, loot and inventory draining are declared services.

The inherited stub chain extracts three Minecraft 1.21.1 bodies from the NeoForge sources cache (`ItemUtils.createFilledResult`, `AbstractContainerMenu.moveItemStackTo`, `Mth.hsvToRgb/hsvToArgb`). When that cache is absent (the cloud worktree cannot reach maven.neoforged.net), `vanilla_substitutes.py` supplies declared reconstructions and the report's `sources_jar.kind` says so. Counts distinguish assertions, independent scenarios and executed production ticks. Compilation and isolated services never prove game, save/chunk reload, GUI, multiplayer or dedicated-server acceptance.
