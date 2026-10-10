# Goal16A 隔离检查边界

这些runner编译并调用选定生产类或逐字抽取的生产方法。它们不是GameTests，也不启动Minecraft客户端/服务器。使用现有JDK21与仓库缓存依赖，输出到 `build/migration/goal16a/<suite>/<unique>/`；每次失败保留，不以编译失败冒充行为回退。

- `verify_goal16a_recipes.py`：真实MixerRecipes/loader/writer、专用同步/客户端/JEI刷新方法；独立解析原版表比较38组/48个有序变体。注册、组件/NBT、tag绑定、网络缓冲/事件调度和JEI对象为明确替身。真实writer导出默认及自定义示例。包含空META、CUSTOM_DATA、UTF-8、非法/超限包、空表/初始化/登录/重发/退出边界。
- `verify_goal16a_machine.py`：实际机器、升级、罐/能源/流体网络和有限Coker衔接方法；世界/注册/菜单/库存掉落等服务替换。206断言/60场景，有限账本另163tick，不计为断言。初始HE/流体/热量明示，未执行完整上游制备。
- `verify_goal16a_structures.py`：抽取生产放置/归属/拆除方法，覆盖四向/逐格/相邻/叠放/替换与代理解析。352断言/72场景。世界、方块状态、loot调用的库存模型为替身；两个回退必须先编译成功再因AssertionError失败。
- `verify_goal16a_acquisition.py`：本批Dura铸锭必要补丁；实际坩埚/模具/铁砧/JEI路径，有限初始材料量与服务替身详见最终报告。旧四铸板/NBT及模具复用检查在此覆盖，不重跑不受影响的全冶金链。
- `verify_goal16a_affected.py`：原样执行Goal15B配方199断言/99场景，只给新loader登记提供空MixerRecipes服务并改变输出目录；旧断言/脚本/生产方法不改。
- `verify_goal16a_resources.py` / `package_goal16a.py`：比对冻结真实起点、生成输入/输出戳、双语、原资产、旧发布包和包内字节；它们属于静态/文件证据。

各report/summary记录生产输入、fixture、适配器、生成替身散列及实际编译/执行命令和返回码；缓存/JDK来源以各报告的散列或版本记录为准。打包再次检查其最终输入，不能用陈旧结果替代冻结源码验证。实际独立场景/断言数量和命令以 `migration/GOAL16A.md` 与 `build/migration/goal16a/verification.json` 为准。
