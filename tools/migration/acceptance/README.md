# Acceptance tools (macOS)

Scripts for real-game acceptance on the Mac: a disposable loopback dedicated server, RCON, up to two dev clients with
their own game directories, an old-version world, log reading and chunk scans, and scripted runs through the acceptance
executor (a dev-only second mod inside the client, see [Scripted runs](#scripted-runs)). Python 3.11.4+ standard library only
(`tarfile` extraction filters);
run everything from the NEO root as `python3 -B -X utf8 tools/migration/acceptance/<script> ...`. State, logs,
backups, client directories and the old world live in `build/migration/accept-goal29/`; nothing here writes to the
tracked tree, the original repository or a real world.

## Authorization boundary

The scripts start offline Gradle runs (`tools/migration/build.sh --offline runServer` / `runClient`), bind only
127.0.0.1, write only `accept-goal29-*` worlds and files under `build/migration/accept-goal29/`, and change files under
`run/` only between a backup and its restore. Each acceptance or smoke run needs the user's authorization for those
effects (dedicated server, second client, disposable world). Nothing is downloaded or installed. NeoForge dev runs
agree to the EULA themselves (`Eula.java:20`), so no `eula.txt` is written.

## Typical session

```sh
python3 -B -X utf8 tools/migration/acceptance/server.py start --tag mp --op alice --op bob
python3 -B -X utf8 tools/migration/acceptance/client.py capture          # once per checkout; needs the session above
python3 -B -X utf8 tools/migration/acceptance/client.py start alice --server 127.0.0.1:25565 --wait-join
python3 -B -X utf8 tools/migration/acceptance/client.py start bob --server 127.0.0.1:25565 --lang zh_cn --wait-join
python3 -B -X utf8 tools/migration/acceptance/rcon.py "list" "give alice hbmsntm:machine_radar_large"
python3 -B -X utf8 tools/migration/acceptance/chat.py --client bob -n 20
python3 -B -X utf8 tools/migration/acceptance/client.py stop bob
python3 -B -X utf8 tools/migration/acceptance/client.py stop alice
python3 -B -X utf8 tools/migration/acceptance/server.py stop
python3 -B -X utf8 tools/migration/acceptance/server.py delete-world --tag mp
```

| Script | Does |
| --- | --- |
| `server.py` | `start` backs up `run/` (server.properties, ops.json, usercache.json, usernamecache.json, options.txt, eula.txt, `config/`, `defaultconfigs/`), writes a one-off loopback configuration (offline mode, flat or `--world-type normal`, peaceful, RCON with a random password kept in `build/migration/accept-goal29/rcon.password`), pre-ops offline UUIDs, starts runServer and waits for `Done`; `stop` sends RCON `stop`, waits for Gradle, restores `run/` byte for byte and checks the hashes; `restart` (same world, run/ not restored in between: edit `run/config` during the session, then restart); `restore`, `status`, `delete-world` (only worlds this tool created), `start --from-world DIR` (loads a copy of a kept world). Not restored: `run/logs/`, `downloads/`, `crash-reports/`, and `banned-*.json`/`whitelist.json` when a run creates them; `start` refuses while any run of the checkout uses `run/`. |
| `rcon.py` | Source RCON client, loopback only; commands from arguments or `-f file`, replies printed in order. |
| `client.py` | `capture` records the runClient JVM command line once (`--argv FILE` keeps a second capture apart); `start NAME` launches a client directly with its own `clients/NAME` game directory, `--username`, preset `options.txt` (`pauseOnLostFocus:false`, `onboardAccessibility:false`, `--lang`, `--option key:value` for key rebinds), and `--server 127.0.0.1:PORT` or `--world NAME` quick play (or neither: title screen), `--jvm-prop KEY=VALUE` (`-D`), `--size WxH`; `stop` kicks over RCON, then TERMs; `status`, `clean`. |
| `drive.py` | Scripted runs: scenarios sent as steps to the acceptance executor, verdicts, `results.json`/`results.md`, reviewer judgments ([Scripted runs](#scripted-runs)). |
| `stations.py` | Builds the user-station world from station scenarios through the dev client, zips it with `STATIONS.md`, reloads it once. |
| `closure.py` | Survival-source closure of an item list from the shipped data plus the machine-recipe and anvil exports of a game run. |
| `chat.py` | `[CHAT]` lines of a client log (`--client NAME` or a path), or the server's lines (`--server`). |
| `oldworld.py` | `extract` (`git archive 66a00353`), `generate` (old runServer, blocks placed over RCON, world kept in `old-world/` with `PLACED.md`), `cleanup`. |
| `assgen.py` | reads `run/config/hbmRecipes` by default; for a single-player client pass `--config build/migration/accept-goal29/clients/<name>/config/hbmRecipes`. |
| `scan_region.py`, `scan_more.py` | Read-only region-file scans: block counts, heights and hosts; `scan_more.py` modes `smolder`, `layers`, `depth`, `willow`, `double`. |
| `findbe.py`, `cellchk.py` | Command lists for block entities / non-air cells in a box (RCON form by default, chat form with a flag). |
| `fluidids.py`, `gencmp.py`, `assgen.py`, `sumloot.py` | Fluid IDs from `Fluids.java`; JAR vs resource trees; assembly-recipe loading commands; `/loot` drop summaries. |

Measured on this Mac (Goal 29C smoke, 2026-11-08): ModDevGradle starts both runs as `java ... @build/moddev/<run>RunVmArgs.txt
-cp ... net.neoforged.devlaunch.Main @build/moddev/<run>RunProgramArgs.txt`, so the launch target and `--gameDir` are in
those files; `client.py start` swaps in its own copy of the program-argument file. A client ended by TERM exits 143
without a crash report; kicking it first puts it on the disconnect screen. Any second run in `run/` (a capture's
runClient, a GameTest server) rotates `run/logs/latest.log` away from a running server, so the server's evidence is its
Gradle-output log `build/migration/accept-goal29/logs/server-<tag>-<time>.log`. A joining client does not log its own
"joined the game"; `--wait-join` asks RCON `list` instead.

## Without Esc

The tools never drive the game window through the operating system. Scripted steps run inside the client through the
acceptance executor (below); for manual play, commands go over RCON on the dedicated server, and in a single-player
world they are typed into chat. Close a container screen with the inventory key and chat with Enter. Whether Esc interrupts the
controlling session on the Mac (it did on Windows), whether the inventory key closes the JEI recipe screen, the Java
app's name in the access list, screenshot and click coordinates, Chinese input methods swallowing letters, and whether
right-click reaches the game are checked by the user at the start of an acceptance run.

## Goal 28 helpers not ported

From `build/migration/accept-goal28/`: `mccmd.ps1`, `mc.sh` (chat injection through PowerShell; use `rcon.py`, or type in
single-player chat), `mclick.ps1`, `keyhold.ps1`, `shiftkey.ps1`, `postkey*.ps1` (Win32 input; the user operates the
window, or computer use once the start-of-run checks allow it), `clientlaunch.ps1` (use `client.py start`), `chat.sh`
(use `chat.py`), and the one-shot shell wrappers (`brk*.sh`, `place*.sh`, `mine.sh`, `harvest.sh`, `plant.sh`,
`bone.sh`, `cry.sh`, `cycle.sh`, `inv.sh`, `loc.sh`, `rf*.sh`, `st.sh`, `vd.sh`, `patch.sh`, `asrun.sh`), which chained
fixed coordinate commands through `mc.sh`, Win32 clicks through `mclick.ps1` and reads through `chat.sh`: put the
commands in a file for `rcon.py -f` (its replies replace the chat reads), and leave the clicks to the player.
`patch.sh` (forceload a patch, unload, scan) becomes `rcon.py "forceload add ..."`, `rcon.py "forceload remove all"` and
`scan_region.py`; `asrun.sh` becomes `assgen.py ... > cmds.txt` and `rcon.py -f cmds.txt`. Goal 28 one-off scripts with fixed coordinates or
item lists (`loot.py`, `loot2.py`, `sl2.py`, `rows.py`, `rec.py`, `layer_check.py`, `setcfg.py`) are not ported;
`s61.py` became `scan_more.py double`.

## Scripted runs

### The executor (`src/acceptance`, mod `hbmaccept`)

A second mod in its own source set (`build.gradle`: `sourceSets.acceptance`, `neoForge.mods.hbmaccept`), compiled with
`tools/migration/build.sh --offline acceptanceClasses`. Only the `client` run loads it (`run.loadedMods`); `data`,
`server` and `gameTestServer` load `hbmsntm` alone, and `jar` packs only the main source set. It is not a stamp input.
Without `-Dhbm.accept.dir=DIR` it logs `hbmaccept: inactive (no -Dhbm.accept.dir)` and registers no listeners; its Mixins
still apply (inert while no step holds a modifier) and JEI still finds its plugin, which only keeps the runtime. With it, it
registers client tick/frame/chat listeners, never blocks, items, data or payloads, and writes no save data of its own.
Its Mixin config (`hbmaccept.mixins.json`) holds `Screen.hasShiftDown/hasControlDown/hasAltDown` (forced true while
the `mod` step holds them, unchanged otherwise), invokers for `MouseHandler.onPress/onMove` and accessors for the sound
engine; `hello.json` reports the modifier self-test.

Steps are files: `DIR/in/NNNNNN.json` (one JSON object, `op` plus fields, written atomically) is executed strictly in
sequence; the result goes to `DIR/out/NNNNNN.json` with `seq`, `op`, `status` (`ok`/`fail`), `reason`, `path` (the
client path taken), `started_ms`, `ended_ms`, `duration_ms`, `ticks`, `frames` and the step's own fields. A step that
times out (`timeout_ticks`), finds no world or screen, takes an empty screenshot or gets a rejected command fails with
the reason. `DIR/shots/` holds screenshots and sheets, `DIR/hello.json` the start record, `DIR/status.json` the state
once a second (in world, window active, fps, last step). Restarting the client continues after the last `out/` file.

| Step | Fields | Path |
| --- | --- | --- |
| `newworld`, `openworld`, `leave`, `quit` | `world` | flat creative world with cheats, seed 31 (`WorldOpenFlows.createFreshLevel`, `WorldPresets.FLAT`); open an existing one; leave like the pause menu (saves); leave, then `Minecraft.stop` |
| `cmd` | `command`, `wait_ticks`, `expect`, `allow_error` | `ClientPacketListener.sendCommand`; the chat lines that arrive within `wait_ticks` (default 4; longer with `expect`) are the reply, a later one is not seen; a red line or a known error text (unknown command, incorrect argument, no player/entity found, could not set the block, no permission, in English or Chinese) rejects it |
| `view` | `pos` or `eye`, `yaw`/`pitch` or `look_at`, `fly`, `hide_gui` | `/tp` as the player, first-person camera; checked to 0.02 block / 0.1° (F1 also hides the block outline) |
| `settle` | `from`, `to`, `ticks` | sections of the box compiled (`LevelRenderer.isSectionCompiled`), compile queue empty, then `ticks` |
| `shot`, `series`, `sheet` | `file`; `count`, `interval`; `tiles`, `cols`, `tile_width/height`, `crop` | `Screenshot.takeScreenshot` after `frames` frames, fails below a luma range of 3; a sheet is a `NativeImage` grid with a label bar and a JSON index |
| `use`, `attack` | `target` {`pos`, `face`, `offset`}, `hold`, `after`, `any_hit` | aims, checks `hitResult`, then presses the bound key through `MouseHandler.onPress` (or `KeyboardHandler.keyPress` when rebound to a key) |
| `key`, `mouse` | `key` (InputConstants name), `button`, `action` (`tap`/`press`/`release`; `click`/`press`/`release`), `hold`, `after`, `at` | `KeyboardHandler.keyPress`; `MouseHandler.onPress/onMove`; two `mouse` clicks with `after: 0` land within the 250 ms of a screen's double click |
| `mod` | `shift`, `control`, `alt` | the Mixin flags above; read back |
| `click`, `widget`, `hover`, `close`, `screen` | `slot`, `at`, `text`/`index`/`class`, `button` | cursor moved and pressed through `MouseHandler`, before/after slot data; the tooltip lines at a slot; `closeContainer` or `setScreen(null)`; the open screen's class |
| `lang` | `code` | `LanguageManager.setSelected`, `reloadResourcePacks`, `options.save` |
| `dump` | `from`, `to`, `faces`, `entities`, `air`, `allow_unloaded`, `render_box` | client block states, block-entity data (client copy: what the server syncs), baked-quad sprites, UVs and tint per face (with empty model data: a model that draws from level data gives its item quads), entities (with `in_render_distance`, and item and count for dropped items and moving belt items); `render_box`: the box the level renderer culls the block entity's renderer by (`BlockEntityRenderer.getRenderBoundingBox`); positions in chunks the client has not loaded fail the step |
| `track`, `sounds`, `perf` | `center`, `radius`, `type`, `ticks`; `action`; `charts` | per-frame entity positions (`max_step`, `reversals`); `SoundManager.addListener` events; fps, frame times, integrated-server tick time |
| `jei` | `action` (`recipes`, `ghost`, `search`, `lookup`), `item`, `target`, `text`, `role` | the executor's own `@JeiPlugin` runtime: recipe focus; the screen's ghost-ingredient targets; the ingredient list after a filter text; the recipe categories and crafting recipes (result, ingredient alternatives) for an item as output or input |
| `export` | `kind` (`anvil`, `crucible`) | writes `DIR/exports/anvil.json` from `AnvilRecipes`, or `DIR/exports/crucible.json`: item → materials by `Mats.getSmeltingMaterialsFromItem` (the crucible's rule) and every mold's cast per material (`MoldItem.Mold.getOutput`); closure.py's inputs |
| `wait`, `chat` | `ticks`; `count`, `expect`, `since_ms` | client ticks; chat lines received since `since_ms` (default: the step's start) |
| `inv`, `itemtip`, `itemmodel` | —; `item` or `slot`; `item` | the player's slots, selected slot, carried stack and game mode; an item's tooltip lines as the client builds them (Shift/Ctrl/Alt from `mod`); the baked item model's sprites (overrides resolved) |
| `tab`, `i18n`, `option` | `tab`; `keys`; `name`, `value` | a creative tab's title and items in order (`CreativeModeTab.getDisplayItems`); translations in the current language (`I18n.get`); set an `options.txt` option |
| `hud`, `preview` | `frames` | the texts drawn on the screen for `frames` frames (`GuiGraphics` string calls; tooltip lines prefixed `tooltip: `), the screen and its GUI origin; the conveyor wand's client preview (present, buildable, blocks with states) |

Scripted input goes through the client's input callbacks, not the operating system: physical keys, system shortcuts,
input methods and window focus are left to user stations.

### drive.py

```sh
python3 -B -X utf8 tools/migration/acceptance/server.py start --tag cap
python3 -B -X utf8 tools/migration/acceptance/client.py capture --argv build/migration/accept-goal29/client-argv-g31e.json
python3 -B -X utf8 tools/migration/acceptance/server.py stop && python3 -B -X utf8 tools/migration/acceptance/server.py delete-world --tag cap
python3 -B -X utf8 tools/migration/acceptance/drive.py list
python3 -B -X utf8 tools/migration/acceptance/drive.py run --run pilot2 --world accept-goal29-g31e-pilot2 conveyor-cranes/crane_faces conveyors/belt_shapes
python3 -B -X utf8 tools/migration/acceptance/drive.py run --run mp2 --group mp acceptance-executor/multiplayer
python3 -B -X utf8 tools/migration/acceptance/drive.py judge build/migration/acceptance-runs/pilot2 conveyors.lift-look --verdict pass --note "..."
```

Re-capture after a class-path change (a new source set or dependency), inside a server session so that `run/` is
restored afterwards (capture ends every dev client of the checkout, so start none before it). The final chain does
not compile `src/acceptance`: after a change to classes it uses (recipes, materials, molds), run `acceptanceClasses`. A solo run starts one client with
`-Dhbm.accept.dir=<run>/<client>`, creates its world with `newworld` (or opens it when it exists), runs the scenarios,
quits the client (the world is saved) and writes `results.json`, `steps.json` and `results.md` under
`build/migration/acceptance-runs/<run>/`. An mp run starts `server.py start --tag` with both players opped, joins two
clients, sends server commands over RCON, then stops the clients, the server (`run/` restored) and deletes the server
world. Single-player and server groups run one after the other (`server.py` refuses while a dev client runs).

Scenarios live in `scenarios/<feature id>/<name>.py` (feature ids of `features.json`): `SCENARIO` (`id` = `<feature>.<name>`,
`group` solo/mp/station, `capture` = window, GUI scale, language, FOV and any camera facts the pictures depend on),
`expectations()` (stable ids starting with the feature id) and `run(ctx)`. `ctx.step(op, **fields)` raises on a failed
step unless `allow_fail=True`; `ctx.check(id, ok, detail, evidence)`, `ctx.review(...)` (a picture for a person),
`ctx.not_run(id, reason)`. Verdicts: pass, fail, review (待人看), not-run (未执行, with the reason). A failed step or a
scenario error ends the scenario and turns every expectation it had not decided into not-run with that reason; a
scenario whose `capture` differs from the run's is not run. Modifier flags are released after every scenario.
`judge` stores a reviewer's verdict in `judgments.json` next to the machine verdict. Scenario files are public: they
cite original source lines, never local migration records.

### stations.py

```sh
python3 -B -X utf8 tools/migration/acceptance/stations.py build --run stations1 conveyors/stations_sample
```

Builds the stations of `group: station` scenarios (`STATIONS`, each with `id`, three short sign lines, `todo`, `expect`,
`build(ctx, x, z)`, `size`) into a fresh world along z = 0, 16 blocks apart: a sign, the content, a copy kept 150 blocks
up as the template, and a stone button on a command block that clones it back. The world is saved, zipped to
`<run>/<world>.zip` with `STATIONS.md` (one row per station, an empty result column; no answer counts as not run),
reopened, and every sign and reset command read back on the server side (`stations.json`, `reload_ok`). After the
reload each station's optional `probe(ctx, x, z)` checks that it works (`probe`), then the content is cleared, the
reset button pressed (the hit must be the button's block) and the restored blocks and container contents compared with
the template (`reset_check`: `same_as_template`, `contents_differ`). Extractors in a template are held still by a
redstone block under them, outside the cloned box, so the template keeps its chest contents; the check holds the
restored extractors the same way while it reads. At most 25 stations. The user needs NeoForge 21.1.228+ with the release jar (and JEI where a station uses it).

### closure.py

```sh
python3 -B -X utf8 tools/migration/acceptance/closure.py --recipes-export <client>/config/hbmRecipes \
    --anvil-export <run>/<client>/exports/anvil.json --crucible-export <run>/<client>/exports/crucible.json \
    hbmsntm:machine_zirnox hbmsntm:settings_tool --json out.json
```

Machine recipe tables exist as JSON only after a game run writes `config/hbmRecipes` (copy them out of a client
directory: `server.py stop` deletes new files under `run/`); the anvil tables and the crucible's melting and casting
only through the executor's `export` step (crucible alloys come from `_hbmCrucible.json`). The report names the exports,
their hashes and the build that wrote them. Not modelled: fluid inputs, items that only come from a process (plants
grown, reactor waste, bedrock ore), and the foundry blocks around the crucible and molds.
