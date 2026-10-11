# Goal17B isolated verification

These new tools reuse existing Goal15A machine and Goal16B structure services without modifying old suites. Run from the NEO repository with the existing Python runtime:

- `python -B -X utf8 tools/migration/verify_goal17b_machine.py`
- `python -B -X utf8 tools/migration/verify_goal17b_structures.py`

Outputs stay under unique directories in `build/migration/goal17b/machine/` and `build/migration/goal17b/structures/`. Every report records source, fixtures, imported adapters, compiled inputs, cached artifacts, Java/javac hashes and exact commands/exit codes. Sources are checked again after each command. A mutation counts only after successful compilation and an expected behavior assertion failure.

The machine world compiles complete production turbofan BE/menu, inventory helpers, charging, upgrades, fluid/power networks, fractionation and ArcFurnace processing. Final ordinary kerosene initialization is extracted from Fluids.init plus its real calculation/round methods. Default pollution derives from real kerosene P_FUEL and PollutionHandler rate declarations; ordinary kerosene burns only SOOT, while its POISON entry is a release map. Synthetic fuel cases are explicitly identified and only cover arithmetic or multi-pollutant edges.

The structure world extracts actual geometry, placement, ownership, proxy and teardown bodies. Minecraft registry, world callbacks, loot generation and core inventory draining are declared services. The cached BlockItem placement-before-consumption order is verified.

Entity tests execute actual BE update/entity methods over instrumented entities. Spatial filtering, damage results, alive status, fire and stuck-in-block calls are services. This proves production call selection/order, blood predicate and push-marking behavior, not vanilla armor, invulnerability, damage cooldown, real death, client transport, cobweb physics or particle/audio appearance.

Finite accounting preloads prepared LIGHTOIL once, executes actual fractionation, then real fluid transfer, turbofan, battery charging and ArcFurnace consumer ticks. Fractionation's electric cost is zero in production. Prepared feed, furnace/electrodes/upgrades and the initial machine are declared inventory boundaries; refinery, manufacture and startup costs are priced separately by the parent. Each ledger closes gross generation against load, charging, all remaining buffers and discarded energy, and records remaining kerosene and diesel. A3 supporting 25,000 HE/t under the recorded finite conditions does not establish net or eternal operation; 125,000 HE/t remains a deficient case.

Counts distinguish assertions, independent scenarios and executed production ticks. Compilation and isolated services never prove game, save/chunk reload, GUI, multiplayer or dedicated-server acceptance.
