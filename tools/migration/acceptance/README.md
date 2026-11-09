# Acceptance tools (macOS)

Scripts for real-game acceptance on the Mac: a disposable loopback dedicated server, RCON, up to two dev clients with
their own game directories, an old-version world, log reading and chunk scans. Python 3.11.4+ standard library only
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
| `client.py` | `capture` records the runClient JVM command line once; `start NAME` launches a client directly with its own `clients/NAME` game directory, `--username`, preset `options.txt` (`pauseOnLostFocus:false`, `onboardAccessibility:false`, `--lang`, `--option key:value` for key rebinds), and `--server 127.0.0.1:PORT` or `--world NAME` quick play (or neither: title screen); `stop` kicks over RCON, then TERMs; `status`, `clean`. |
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

The tools never drive the game window. Commands go over RCON on the dedicated server; in a single-player world they are
typed into chat. Close a container screen with the inventory key and chat with Enter. Whether Esc interrupts the
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
