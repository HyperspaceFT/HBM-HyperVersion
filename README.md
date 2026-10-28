# HBM-HyperVersion

**English** | [中文](README.zh_CN.md)

Hbm's Nuclear Tech Mod for Minecraft 1.21.1 on NeoForge, continued as a feature-by-feature port of the original 1.7.10 mod.

> **This mod is heavy vibe coded.** Most of the code is written by AI agents working from the original source, with review and in-game checks along the way. If you do not like software made this way, feel free to leave.

The mod id is `hbmsntm`. The code base started from *Hbm's Nuclear Tech: Neo Edition*, the 1.21.1 port by ohiomannnn, and this repository carries that work forward: the original [Hbm's Nuclear Tech Mod](https://github.com/HbmMods/Hbm-s-Nuclear-Tech-GIT) by The Bobcat is the behavioral reference, and its machines, materials, recipes and mechanics are ported batch by batch onto NeoForge 1.21.1 APIs.

## Status

This mod is in active development and is **not ready for survival worlds**. Content is still missing, recipes and balance change between versions, and saved worlds may stop loading after an update. Use a disposable world.

Each ported batch is checked with GameTests and in-game acceptance runs on the single-player client and the dedicated server, but many areas of the original remain untouched. The version tag (`198A`) follows the Neo Edition base it builds on.

## What is in so far

Ported so far, in rough progression order:

- Ore processing: crushing, pressing, scrap and powders.
- Heat processing, coking and the basic carbon materials.
- Energy storage and generation: creosote burners, Stirling engines, boilers, steam condenser and steam engine, industrial boiler.
- Fluid logistics: pipes, tanks, pumps and fluid-aware recipes.
- Crucible smelting with multi-material alloys, casting pools, channels and the foundry casting chain with molds and basins.
- Welding, heating furnace, electric furnace, arc furnace and the silicon and chip chain.
- Oil drilling and burning, refinery, catalytic cracking, chemical plant and Desh.
- Blueprint circuits, concrete, the material table with the original 109 materials, crucible alloys and the Tier 4 anvil.
- The RBMK reactor with its columns, fuel channels and control rods.
- Radiation hazards with Geiger counter, dosimeter and diagnostic readouts.
- JEI recipe categories for the ported machines.
- Simplified Chinese localization maintained together with the English text.

## Installation

The mod has no required dependencies.

1. Install NeoForge 21.1.228 or newer on Minecraft 1.21.1 (Java 21).
2. Launch the game once so the `mods` folder exists.
3. Drop the mod jar into `.minecraft/mods`.

JEI is supported but optional.

## Building from source

```bash
./gradlew.bat build
```

The jar is written to `build/libs/`. On other platforms use `./gradlew` with the same tasks. `./gradlew.bat runData` regenerates the datagen output under `src/generated/resources`; `runClient`, `runServer` and `runGameTestServer` are the declared run configurations.

## Repository layout

- `src/main/java/com/hbm` – mod code, entry point `com.hbm.main.NuclearTechMod`.
- `src/main/java/com/hbm/datagen` – data generators; the generated resources live in `src/generated/resources`.
- `src/main/java/com/hbm/gametest` – GameTests for the ported behavior.
- `src/main/resources/assets/hbmsntm` – hand-written assets, including `lang/zh_cn.json`.
- `tools/migration` – verification, packaging and localization audit scripts used while porting.

## Known issues

- Iris shaders break parts of the custom rendering.

## Contributing

This is a personal project without a formal contribution process. Issues are read, but there is no commitment to triage or merge external changes.

## Credits

- Hbm's Nuclear Tech Mod by [The Bobcat (HbmMods)](https://github.com/HbmMods).
- Hbm's Nuclear Tech: Neo Edition by ohiomannnn, the 1.21.1 port this repository builds on ([CurseForge](https://www.curseforge.com/minecraft/mc-mods/hbms-nuclear-tech-ne), [Modrinth](https://modrinth.com/mod/hbms-nuclear-tech-ne)).
- The NeoForged team for NeoForge and Mojang for Minecraft.

## License

This software is licensed under the GNU Lesser General Public License version 3. You may run it, modify it and distribute it or modified versions, as long as the modified software is also free software; linking to it is exempt under the "Lesser" terms. The full text is in `LICENSE` and `LICENSE.LESSER`.
