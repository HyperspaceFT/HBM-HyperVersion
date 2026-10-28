# HBM-HyperVersion

[English](README.md) | **中文**

Hbm's Nuclear Tech Mod 的 Minecraft 1.21.1 NeoForge 版本，以逐功能移植原版 1.7.10 内容的方式持续开发。

> **本模组为 Heavy Vibe Coded。** 绝大部分代码由 AI 代理对照原版源码编写，过程中辅以审查与实机检查。如果你不喜欢这类编程方式制成的产物，feel free to leave。

模组 id 为 `hbmsntm`。代码基于 ohiomannnn 的 1.21.1 移植版 *Hbm's Nuclear Tech: Neo Edition*，本仓库在其基础上继续推进：以 The Bobcat 的原版 [Hbm's Nuclear Tech Mod](https://github.com/HbmMods/Hbm-s-Nuclear-Tech-GIT) 为行为基准，把原版的机器、材料、配方和机制分批移植到 NeoForge 1.21.1 的 API 上。

## 状态

模组仍在开发中，**不适合生存存档**。内容尚有缺失，配方和数值会在版本之间变动，更新后旧存档可能无法加载。请使用一次性世界。

每一批移植都经过 GameTest 以及单人客户端和专用服务器上的实机验收，但原版仍有大量内容尚未移植。版本号（`198A`）沿用所基于的 Neo Edition 版本。

## 已移植内容

大致按进度顺序：

- 矿物处理：粉碎、压制、碎料与粉末。
- 热加工、炼焦与基础碳材料。
- 储能与发电：杂酚油燃烧、斯特林发动机、锅炉、蒸汽冷凝器与蒸汽机、工业锅炉。
- 流体物流：管道、储罐、水泵与含流体的配方。
- 坩埚多材料熔炼与合金、铸造池、浇道，以及带铸模和铸造盘的铸造链。
- 焊接、加热炉、电炉、电弧炉与硅／芯片链。
- 原油开采与燃烧、炼油厂、催化裂化、化工厂与 Desh。
- 蓝图电路、混凝土、原版 109 种材料的材料表、坩埚合金与 4 级铁砧。
- RBMK 反应堆及其堆柱、燃料通道与控制棒。
- 辐射危害，含盖革计数器、剂量计与诊断读数。
- 已移植机器的 JEI 配方分类。
- 与英文同步维护的简体中文汉化。

## 安装

模组没有必需的前置。

1. 在 Minecraft 1.21.1（Java 21）上安装 NeoForge 21.1.228 或更新版本。
2. 启动一次游戏以生成 `mods` 文件夹。
3. 把模组 jar 放入 `.minecraft/mods`。

支持 JEI，但不是必需。

## 从源码构建

```bash
./gradlew.bat build
```

产物在 `build/libs/`。其他平台用 `./gradlew` 执行同样的任务。`./gradlew.bat runData` 重新生成 `src/generated/resources` 下的数据生成输出；`runClient`、`runServer` 和 `runGameTestServer` 是声明的运行配置。

## 仓库结构

- `src/main/java/com/hbm`：模组代码，入口为 `com.hbm.main.NuclearTechMod`。
- `src/main/java/com/hbm/datagen`：数据生成器，生成的资源位于 `src/generated/resources`。
- `src/main/java/com/hbm/gametest`：已移植行为的 GameTest。
- `src/main/resources/assets/hbmsntm`：手写资源，包括 `lang/zh_cn.json`。
- `tools/migration`：移植过程中使用的验证、打包与汉化审计脚本。

## 已知问题

- Iris 光影会破坏部分自定义渲染。

## 参与

这是个人项目，没有正式的贡献流程。Issue 会被阅读，但不承诺处理或合并外部修改。

## 致谢

- Hbm's Nuclear Tech Mod，作者 [The Bobcat (HbmMods)](https://github.com/HbmMods)。
- Hbm's Nuclear Tech: Neo Edition，作者 ohiomannnn，本仓库所基于的 1.21.1 移植版（[CurseForge](https://www.curseforge.com/minecraft/mc-mods/hbms-nuclear-tech-ne)、[Modrinth](https://modrinth.com/mod/hbms-nuclear-tech-ne)）。
- NeoForged 团队的 NeoForge 与 Mojang 的 Minecraft。

## 许可

本软件以 GNU 宽通用公共许可证第 3 版（LGPL-3.0）发布。你可以自由运行、修改和分发本软件及其修改版本，前提是修改后的软件同样采用自由软件许可；按 "Lesser" 条款，仅链接本软件不受此限制。完整文本见 `LICENSE` 与 `LICENSE.LESSER`。
