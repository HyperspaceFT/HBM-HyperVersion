# Goal17A isolated acquisition regression

Run from the NEO root with the existing bundled Python, without bytecode output:

```powershell
& 'C:/Users/显卡超频和烤机测试/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -B tools/migration/verify_goal17a_acquisition.py
```

The runner compiles the actual named foundry, crucible, material, casting/JEI and smithing production classes against inherited service stand-ins. Each invocation creates only `build/migration/goal17a/acquisition/<uuid>` stubs, adapted old Java fixture, source argument file, classes, transcript and report. It hashes initial/final production and fixture inputs, generated stubs and adapted Java, cached Gson and Java/javac executables. Failed attempts are preserved; a compile failure is infrastructure failure, not detection of a production behavioral regression.

The old Goal16A Java fixture stays byte-for-byte unchanged on disk. Exactly one `recipes.size() == 5` becomes `== 6`, and exactly three `recipes.getLast()` become `recipes.get(4)` in the run directory. This precise adapter preserves all 49 old behavioral assertions, including the four plate outputs, 72q Dura, valid old NBT, anvil matching and JEI Dura row. The new suite independently requires six ordered rows with the appended 216q tungsten blade row.

The blade suite covers both actual tier-one blade samples, strict count and ordering, component-preserving sample reuse and split mold insertion, wrong/empty samples, no mold, wrong material, partial/full/oversized/repeated offers, output blocking, 199/200 full ticks, server/client guards, NBT and sync capacities/material validation, partial and cooling roundtrips, legacy plate saves, mold/output components, reusable mold, scrap account, output extraction and declared sided inventory rules.

Finite acquisition preloads the actual crucible material buffer once with 1728q tungsten (24 ingots). Nine accepted 24q transfers fill each blade mold; eight casts yield eight blades and zero tungsten remainder. There is no replenishment. Existing recipe source is checked for 2 titanium plates plus 4 titanium ingots -> 2 titanium blades and 8 tungsten blades plus 1 Dura ingot -> 1 tungsten rotor. The rotor Dura is explicitly separate supplied stock, with its upstream 24q tungsten cost excluded from the 1728q blade ledger. The crafting engine is not executed.

Evidence boundary: Minecraft world/container/network services, item/component serialization, registry and JEI services are stand-ins. Automated extraction is checked through actual sided-inventory declarations plus the stand-in inventory removal operation, not a real hopper. Block use and AnvilMenu consumption bridges are statically checked. No real gameplay, actual save file reload, GUI/JEI rendering, multiplayer, dedicated server, or upstream material acquisition is established. Parent owns Gradle/datagen, resource/localization/JAR audits and acceptance.
