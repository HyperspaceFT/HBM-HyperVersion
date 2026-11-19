#!/usr/bin/env python3
"""Old-version worlds for save-upgrade checks: build a world with an earlier release, open it on the current build, compare.

Two ways to run an earlier release (both offline; nothing is downloaded, nothing under .git changes, no worktree):
  path A (jar)     the release JAR in the dev environment: the dev server's JVM command line without NEO's own mod
                   folders, a game root of its own with the JAR in run/mods/ (prepare-jar, then server.py --java-argv).
  path B (source)  the tag's source tree from `git archive <tag>`, built and run offline with its own runServer
                   (extract), Gradle against this repository's .gradle/user-home; a missing dependency stops it.

Run from the NEO root (every command takes --work DIR, default build/migration/accept/oldworld; the Goal 32G lane uses
--work build/migration/goal32g/oldworld):
  oldworld.py capture-server                         # while server.py runs NEO's own dev server: its JVM command line
  oldworld.py prepare-jar --tag v0.30.0 --jar build/migration/release-v0.30.0/HBM-HyperVersion-0.30.0.jar
  oldworld.py trial-jar --tag v0.30.0                # path A trial: does the dev server load the JAR instead of NEO?
  oldworld.py extract --tag v0.29.1                  # path B: git archive into <work>/src-<tag>/
  oldworld.py prepare-client --tag v0.30.0 --name g32g_old030   # optional: an old-version dev client (path A only)
  oldworld.py generate --tag v0.30.0 --mode jar [--player g32g_old030]
  oldworld.py control                                # optional: the current build on a fresh world, same load steps
  oldworld.py load --tag v0.30.0 [--player g32g_old030]
  oldworld.py compare --tag v0.30.0 [--control-log FILE]
  oldworld.py fixture --tag v0.30.0 --name v0.30-goal32g-oldworld.zip
  oldworld.py cleanup --tag v0.30.0 [--worlds]
  oldworld.py plan --tag v0.30.0                     # print the world plan (commands, cells, injected fields)

generate starts the old server (server tag g32g-gen-<version>), makes the radiation (gas_meltdown under open sky, the
world running for --rad-seconds), freezes the world, places the plan of plan() over RCON, reads it back, removes the
chunk tickets, saves and stops; the world moves to <work>/world-<tag>/ with placed.json and PLACED.md.
load copies that world into the current build's dev server (server.py start --from-world), freezes, loads the chunks,
marks them unsaved, saves, copies the saved world to <work>/loaded-<tag>/ while the server runs, then reads the
functional checks F1-F4 (100 ticks with `tick step`), stops and deletes the server's copy.
compare applies migration/goal32g-oldworld-criteria.md through oldworld_compare.py.
Logs and RCON transcripts go to <work>/logs/. Server tags (and so world names) start with g32g-.
"""
import argparse
import io
import json
import re
import shutil
import subprocess
import sys
import tarfile
import time
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import oldworld_compare as oc  # noqa: E402
from oldworld_compare import B, S, I, L, F, D, STR, LIST, C  # noqa: E402

DEFAULT_WORK = common.STATE / 'oldworld'
BUILD_FILES = ('build.gradle', 'gradle.lockfile', 'settings.gradle', 'gradle.properties',
               'gradle/wrapper/gradle-wrapper.properties', 'tools/migration/build.sh')
LOCK_ANCHOR = '    lockAllConfigurations()\n'
LOCK_LINES = ("    // Minecraft ships this library for macOS only, so the runtime classpaths resolve it on macOS and nowhere else.\n"
              "    ignoredDependencies.add('ca.weblite:java-objc-bridge')\n")
MODDEV = common.REPO / 'build' / 'moddev'
CLIENT_ARGV = common.STATE / 'client-argv.json'
FLUIDS_JAVA = 'src/main/java/com/hbm/inventory/fluid/Fluids.java'
H = 'hbmsntm:'

# ---------------------------------------------------------------- the world plan

Y = -60                   # flat world: grass at y=-61, everything stands on y=-60
X0, Z0 = 512, 512         # build area: chunks 32..35 x 32..35, 32 chunks from the spawn chunk
AREA = ((X0, Z0), (X0 + 63, Z0 + 63))
# Radiation source chunk; the measured area is the 7 x 7 chunks around it. Far from the build area: chunk radiation spreads
# a chunk a second and turns grass into waste earth wherever a chunk holds 10 or more (ChunkRadiationHandlerSimple.java:
# 84-103, 186-224), also while the world is frozen (ChunkRadiationManager.java:59-73 runs on the server tick event).
RAD_CHUNK = (56, 33)
RAD_HALF = 3
RAD_GAS = ((900, Y + 1, 532), (906, Y + 3, 538))
RAD_CLEAN = ((888, Y - 1, 520), (919, Y + 20, 551))
V030, V031 = (0, 30, 0), (0, 31, 0)


def in_area(pos):
    return AREA[0][0] <= pos[0] <= AREA[1][0] and AREA[0][1] <= pos[2] <= AREA[1][1]


def version(tag):
    m = re.fullmatch(r'v?(\d+)\.(\d+)\.(\d+)', tag)
    if not m:
        raise SystemExit('--tag must look like v0.30.0')
    return tuple(int(x) for x in m.groups())


def key_of(tag):
    return tag.replace('.', '')


def fluid_ids():
    import fluidids
    return fluidids.fluid_ids()


def item(slot, iid, count=1, components=None):
    d = dict(Slot=B(slot), id=STR(iid), count=I(count))
    if components:
        d['components'] = C(components)
    return C(d)


def rotate(dims, facing):
    """MultiblockHandlerXR.rotate (MultiblockHandlerXR.java:107-128): dims are U, D, N, S, W, E when looking south."""
    u, d, n, s, w, e = dims
    return {'south': [u, d, n, s, w, e], 'north': [u, d, s, n, e, w],
            'east': [u, d, e, w, n, s], 'west': [u, d, w, e, s, n]}[facing]


def multiblock(block, core, dims, facing='north', extras=(), core_nbt=None, core_props=None, cell_props=None):
    """(pos, state, nbt) of a whole DummyableBlock multiblock as MultiblockHandlerXR.fillSpace (:53-104) places it, core first and
    every dummy after the cell it points to (its chain to the core is its Manhattan distance), so no dummy is ever an orphan
    (DummyableBlock.destroyIfOrphan, DummyableBlock.java:135-151). extras are offsets from the core that get type=extra
    (the block's makeExtra positions)."""
    x, y, z = core
    rot = rotate(dims, facing)
    extra = {(x + a, y + b, z + c) for a, b, c in extras}
    props = dict(cell_props or {})
    cells = [((x, y, z), '%s[%s]' % (block, ','.join('%s=%s' % kv for kv in dict(facing=facing, type='core', **(core_props or props)).items())), core_nbt)]
    rest = []
    for a in range(x - rot[4], x + rot[5] + 1):
        for b in range(y - rot[1], y + rot[0] + 1):
            for c in range(z - rot[2], z + rot[3] + 1):
                if b < y:
                    f = 'down'
                elif b > y:
                    f = 'up'
                elif a < x:
                    f = 'west'
                elif a > x:
                    f = 'east'
                elif c < z:
                    f = 'north'
                elif c > z:
                    f = 'south'
                else:
                    continue
                t = 'extra' if (a, b, c) in extra else 'dummy'
                state = '%s[%s]' % (block, ','.join('%s=%s' % kv for kv in dict(facing=f, type=t, **props).items()))
                rest.append((abs(a - x) + abs(b - y) + abs(c - z), (a, b, c), state))
    for _, pos, state in sorted(rest):
        cells.append((pos, state, None))
    return cells


def plan(tag):
    """The content of the old world for one version: pieces with their cells (in placing order), the block entities they
    inject, where to touch pipes and cables so they compute their connections with every neighbour in place, and the
    functional probes. Every block entity field used here is the one its saveAdditional writes at the tag (cited)."""
    v = version(tag)
    fl = fluid_ids()
    W, UF6, CO2, SHS = fl['WATER'], fl['UF6'], fl['CARBONDIOXIDE'], fl['SUPERHOTSTEAM']

    def tank(name, fill, cap, ftype):
        # FluidTank.writeToNBT (FluidTank.java): name, name_max, name_type (numeric ID), name_p; readFromNBT clamps the fill to
        # the saved maximum, so the maximum is written as the machine's real capacity.
        return {name: I(fill), name + '_max': I(cap), name + '_type': I(ftype), name + '_p': S(0)}

    pieces = []

    def piece(name, since, cells, why, touch=(), entities=(), after=()):
        if v >= since:
            pieces.append(dict(name=name, why=why, cells=cells, touch=list(touch), entities=list(entities), after=list(after)))

    # Stage 1 (materials): a chest of mod items, one with a data component.
    piece('materials-chest', (0, 0, 0), [((X0, Y, Z0 + 2), 'minecraft:chest[facing=north]', C(dict(Items=LIST([
        item(0, H + 'ingot_steel', 64), item(1, H + 'plate_steel', 32), item(2, H + 'canister_empty', 5),
        item(3, H + 'nugget_uranium', 9), item(4, H + 'waste_uranium', 2), item(5, H + 'rbmk_fuel_ueu', 1),
        item(6, H + 'fluid_identifier_multi', 1), item(7, H + 'rod_zirnox', 1, {H + 'meta': I(3)}),
        item(8, 'minecraft:iron_ingot', 10)]))))],
          'item ids and a data component (NtmDataComponents.java:17, hbmsntm:meta) in a vanilla container')
    # Stage 10: spent fuel in a waste drum (MachineBaseBlockEntity slots only).
    piece('waste-drum', (0, 0, 0), [((X0 + 2, Y, Z0 + 2), H + 'machine_waste_drum', C(dict(Items=LIST([
        item(0, H + 'waste_natural_uranium', 2)]))))],
          'MachineWasteDrumBlockEntity: Items (MachineBaseBlockEntity saveAdditional)')
    # Stage 2: blast furnace core only (MachineBlastFurnaceBlockEntity saveAdditional: fuel, progress, speed, isProgressing, tanks).
    piece('blast-furnace-core', (0, 0, 0), [((X0 + 6, Y, Z0 + 2), H + 'machine_blast_furnace[facing=north,type=core]', C(dict(
        fuel=I(400), progress=F(0.5), speed=F(0.25), isProgressing=B(0),
        Items=LIST([item(0, 'minecraft:iron_ingot', 8)]))))],
          'core only (setblock cannot run the player placement); the block entity is what loading reads')
    # Stage 4: assembly machine core (power, maxPower, the module's recipe0/progress0: ModuleMachineBase.java:243-249).
    piece('assembly-machine-core', (0, 0, 0), [((X0 + 12, Y, Z0 + 2), H + 'machine_assembly_machine[facing=north,type=core]', C(dict(
        power=L(40000), maxPower=L(100000), recipe0=STR('ass.machine_refinery'), progress0=D(0.25))))],
          'core only; the block entity class changed between v0.30.0 and v0.31.0')
    # Stage 8: ZIRNOX core with heat, pressure, three tanks and two rods (ReactorZirnoxBlockEntity saveAdditional).
    zir = dict(heat=I(5000), pressure=I(1500), isOn=B(0), redstonePowered=B(0),
               Items=LIST([item(0, H + 'rod_zirnox', 1, {H + 'meta': I(1)}), item(1, H + 'rod_zirnox', 1, {H + 'meta': I(2)})]))
    zir.update(tank('water', 20000, 32000, W))
    zir.update(tank('carbondioxide', 8000, 16000, CO2))
    zir.update(tank('steam', 0, 8000, SHS))
    piece('zirnox-core', (0, 0, 0), [((X0 + 20, Y, Z0 + 2), H + 'machine_zirnox[facing=north,type=core]', C(zir))],
          'core only; fluid tanks and rods with a data component')
    # Armor stand with living attachments (ntmprops, LivingPropsCommand.java:41-60): attachment save without a client.
    piece('living-attachments', (0, 0, 0), [], 'HbmLivingAttachments on a non-player living entity',
          entities=['summon minecraft:armor_stand %.1f %d %.1f {Tags:["g32g"],NoGravity:1b,Invulnerable:1b}' % (X0 + 28.5, Y, Z0 + 2.5)],
          after=['ntmprops set @e[type=minecraft:armor_stand,tag=g32g,limit=1] %s %s' % kv
                 for kv in (('radiation', '123.5'), ('digamma', '0.25'), ('asbestos', '40'), ('blacklung', '60'))])

    # A multiblock with pipes on its outer blocks (GOAL31D-ACCEPTANCE 11.3): the pipes are placed first, the press after, then
    # every pipe is touched so it computes its arms with the old version's rules (FluidDuctStandardBlock.updateShape).
    pz = Z0 + 10
    piece('press-with-pipes', (0, 0, 0),
          [((X0 + 3, Y + 1, pz), H + 'fluid_duct_neo', C(dict(Type=I(W)))),
           ((X0 + 1, Y + 2, pz), H + 'fluid_duct_neo', C(dict(Type=I(W))))] +
          multiblock(H + 'machine_press', (X0 + 2, Y, pz), [2, 0, 0, 0, 0, 0], core_nbt=C(dict(
              press=I(40), burnTime=I(1200), speed=I(50), ret=B(0),
              Items=LIST([item(0, 'minecraft:coal', 16), item(2, H + 'ingot_steel', 4)])))),
          'MachinePressBlock dims {2,0,0,0,0,0} (MachinePressBlock.java:41); pipes beside the two upper cells',
          touch=[((X0 + 3, Y + 1, pz), (0, 0, 1)), ((X0 + 1, Y + 2, pz), (0, 0, 1))])
    # Stage 7: gas centrifuge, whole, with a UF6 pipe on an extra cell (MachineGasCentrifugeBlock.java:51-61).
    piece('gas-centrifuge', (0, 0, 0),
          [((X0 + 7, Y + 1, pz), H + 'fluid_duct_neo', C(dict(Type=I(UF6))))] +
          multiblock(H + 'machine_gas_centrifuge', (X0 + 6, Y, pz), [3, 0, 0, 0, 0, 0], extras=[(0, 1, 0), (0, 2, 0), (0, 3, 0)],
                     core_nbt=C(dict(power=L(40000), progress=S(100), isProgressing=B(0), **tank('tank', 1000, 2000, UF6)))),
          'whole multiblock with its three extra cells; a pipe on an extra cell',
          touch=[((X0 + 7, Y + 1, pz), (0, 0, 1))])
    # Stage 9: a small fuelled RBMK, 3 x 3 columns, each a whole column (RBMKBaseBlock.java:76-88: dims {height-1,0,...},
    # extra on top; dialColumnHeight 4 by default, CommonConfig.java:575-578).
    rx, rz = X0 + 28, Z0 + 8
    layout = [['rbmk_blank', 'rbmk_blank', 'rbmk_blank'], ['rbmk_blank', 'rbmk_rod', 'rbmk_control'], ['rbmk_blank', 'rbmk_blank', 'rbmk_blank']]
    rbmk = []
    for r, row in enumerate(layout):
        for c, col in enumerate(row):
            if col == 'rbmk_rod':
                nbt = C(dict(heat=D(450.0), hasRod=B(1), Items=LIST([item(0, H + 'rbmk_fuel_ueu', 1)])))
            elif col == 'rbmk_control':
                nbt = C(dict(heat=D(300.0), level=D(0.6), targetLevel=D(0.6), startingLevel=D(0.6)))
            else:
                nbt = C(dict(heat=D(120.0 + 10 * (r * 3 + c))))
            rbmk += multiblock(H + col, (rx + c, Y, rz + r), [3, 0, 0, 0, 0, 0], extras=[(0, 3, 0)], core_nbt=nbt,
                               cell_props=dict(lid='none'))
    piece('rbmk-small', (0, 0, 0), rbmk, '3 x 3 RBMK: one fuel channel with a natural uranium rod, one manual control rod, seven blanks')

    # Stage 3 and the power segment: a wood burner (whole; power ports two blocks behind the core, MachineWoodBurnerBlockEntity.java:
    # 226-236) feeding an electric furnace over a cable that crosses the chunk border at z = 544.
    bz = Z0 + 18
    cables = [((X0, Y, z), H + 'red_cable', None) for z in range(bz + 2, Z0 + 38)]
    piece('power-segment', (0, 0, 0), cables +
          multiblock(H + 'machine_wood_burner', (X0, Y, bz), [1, 0, 1, 0, 1, 0], extras=[(0, 0, 1), (1, 0, 1)],
                     core_nbt=C(dict(power=L(60000), burnTime=I(200), maxBurnTime=I(400), isOn=B(1), liquidBurn=B(0),
                                     ashLevelWood=I(3), ashLevelCoal=I(0), ashLevelMisc=I(0),
                                     Items=LIST([item(0, 'minecraft:oak_log', 16)])))) +
          [((X0, Y, Z0 + 38), H + 'machine_electric_furnace', C(dict(power=L(0), progress=I(0))))],
          'generator -> cable across a chunk border -> consumer (F1)',
          touch=[((X0, Y, z), (-1, 0, 0)) for z in range(bz + 2, Z0 + 38)])
    # The fluid segment: an output barrel, pipes across the chunk border at x = 528, an input barrel (BarrelBlockEntity: mode 0 input,
    # 2 output, BarrelBlockEntity.java:295-300; barrel_steel holds 16,000 mB, NtmBlocks.java:427).
    fz = Z0 + 44
    pipes = [((x, Y, fz), H + 'fluid_duct_neo', C(dict(Type=I(W)))) for x in range(X0 + 1, X0 + 18)]
    piece('fluid-segment', (0, 0, 0), pipes +
          [((X0, Y, fz), H + 'barrel_steel', C(dict(mode=S(2), **tank('tank', 6000, 16000, W)))),
           ((X0 + 18, Y, fz), H + 'barrel_steel', C(dict(mode=S(0), **tank('tank', 1000, 16000, W))))],
          'output barrel -> pipes across a chunk border -> input barrel (F2)',
          touch=[((x, Y, fz), (0, 0, -1)) for x in range(X0 + 1, X0 + 18)])

    # v0.31.0: items on belts (belts take the input side as their facing, ConveyorBaseBlock.java:34-36) and an extractor whose filter
    # stores a tag name (ModulePatternMatcher.java:137-150; CraneExtractorBlockEntity.java:281-293).
    cz = Z0 + 52
    piece('belt-items', V031, [((x, Y, cz), H + 'conveyor[facing=west]', None) for x in range(X0, X0 + 8)],
          'a straight belt with a moving item (F3)',
          entities=['summon hbmsntm:moving_item %.1f %.2f %.1f {Item:{id:"minecraft:iron_ingot",count:3}}' % (X0 + 0.5, Y + 0.25, cz + 0.5)])
    piece('crane-tag-filter', V031,
          [((X0 + 12, Y, cz), 'minecraft:chest[facing=north]', C(dict(Items=LIST([
              item(0, 'minecraft:iron_ingot', 16), item(1, 'minecraft:gold_ingot', 16)])))),
           ((X0 + 13, Y, cz), H + 'crane_extractor[input=east,output=west]', C(dict(
               isWhitelist=B(1), maxEject=B(0), mode0=STR('c:ingots/iron'), Items=LIST([item(0, 'minecraft:iron_ingot', 1)]))))],
          'whitelist extractor, filter slot 0 in tag mode c:ingots/iron, pulling from the chest west of it (F4)')

    area_chunks = oc.chunk_range(AREA)
    # Every cell lies inside the build area: the load forceloads only the area's chunks and the comparison reads only them, so
    # a cell outside would neither load as ticking nor be compared. (A touch is placed and removed again; it may lie outside.)
    outside = [pos for pc in pieces for pos, state, nbt in pc['cells'] if not in_area(pos)]
    if outside:
        raise SystemExit('cells outside the build area %s: %s' % (AREA, outside[:5]))
    rad_chunks = [(RAD_CHUNK[0] + i, RAD_CHUNK[1] + j) for i in range(-RAD_HALF, RAD_HALF + 1) for j in range(-RAD_HALF, RAD_HALF + 1)]
    functional = dict(
        F1=dict(kind='increase', pos=[X0, Y, Z0 + 38], path='power', since=[0, 0, 0]),
        F2=dict(kind='increase', pos=[X0 + 18, Y, fz], path='tank', since=[0, 0, 0]),
        F3=dict(kind='moved', selector='@e[type=hbmsntm:moving_item,x=%d,y=%d,z=%d,dx=12,dy=2,dz=1,limit=1]' % (X0 - 2, Y - 1, cz),
                since=list(V031)),
        F4=dict(kind='filter', chest=[X0 + 12, Y, cz], take='minecraft:iron_ingot', keep='minecraft:gold_ingot', since=list(V031)))
    return dict(tag=tag, version=list(v), y=Y, area=[list(AREA[0]), list(AREA[1])], area_chunks=[list(c) for c in area_chunks],
                radiation=dict(key='hfr_simple_radiation', source_chunk=list(RAD_CHUNK), chunks=[list(c) for c in rad_chunks],
                               gas=[list(RAD_GAS[0]), list(RAD_GAS[1])], meaningful_min=10, keep_ratio=0.5, max_window_s=30),
                pieces=pieces, functional={k: f for k, f in functional.items() if v >= tuple(f['since'])})


def forceload_boxes(p):
    (ax0, az0), (ax1, az1) = p['area']
    rc = p['radiation']['chunks']
    rx0, rz0 = min(c[0] for c in rc) * 16, min(c[1] for c in rc) * 16
    rx1, rz1 = max(c[0] for c in rc) * 16 + 15, max(c[1] for c in rc) * 16 + 15
    return [(ax0, az0, ax1, az1), (rx0, rz0, rx1, rz1)]


def setblock(pos, state, nbt):
    return 'setblock %d %d %d %s%s' % (pos[0], pos[1], pos[2], state, oc.snbt(nbt) if nbt else '')


def build_commands(p):
    out = []
    for pc in p['pieces']:
        for pos, state, nbt in pc['cells']:
            out.append(setblock(pos, state, nbt))
        out += pc['entities'] + pc['after']
        for (x, y, z), (dx, dy, dz) in pc['touch']:
            # A neighbour placed and removed makes the pipe or cable recompute its connections with every neighbour in place.
            out += ['setblock %d %d %d minecraft:stone' % (x + dx, y + dy, z + dz), 'setblock %d %d %d minecraft:air' % (x + dx, y + dy, z + dz)]
    return out


def probes(p):
    """Positions whose block data is read back: every cell that got block-entity data."""
    return [pos for pc in p['pieces'] for pos, state, nbt in pc['cells'] if nbt is not None]


def readback_commands(p):
    out = ['data get block %d %d %d' % pos for pos in probes(p)]
    out += ['execute if block %d %d %d %s' % (pos[0], pos[1], pos[2], state) for pc in p['pieces'] for pos, state, nbt in pc['cells']]
    out += ['data get entity @e[type=minecraft:armor_stand,tag=g32g,limit=1]',
            'execute if entity @e[type=hbmsntm:moving_item]', 'tick query']
    return out


def flatten(tag, path=''):
    """{path: plain value} of an injected typed value, in the path form oldworld_compare._get_path reads."""
    t, v = tag
    out = {}
    if t == oc.COMPOUND:
        for k, x in v.items():
            out.update(flatten(x, '%s.%s' % (path, k) if path else k))
    elif t == oc.LIST_T and v[0] == oc.COMPOUND and v[1] and all('Slot' in x for x in v[1]):
        for x in v[1]:
            out.update(flatten((oc.COMPOUND, x), '%s[Slot=%d]' % (path, x['Slot'][1])))
    else:
        out[path] = oc.plain(tag)
    return out


def placed_json(p, tag, mode, extra):
    injected = [dict(piece=pc['name'], pos=list(pos), fields=flatten(nbt))
                for pc in p['pieces'] for pos, state, nbt in pc['cells'] if nbt is not None]
    pieces = [dict(name=pc['name'], why=pc['why'], cells=[[list(pos), state] for pos, state, nbt in pc['cells']],
                   entities=pc['entities'], after=pc['after']) for pc in p['pieces']]
    return dict(tag=tag, mode=mode, version=p['version'], area=p['area'], area_chunks=p['area_chunks'], radiation=p['radiation'],
                functional=p['functional'], pieces=pieces, injected=injected, **extra)


def placed_md(data):
    lines = ['# Old-version world (%s, %s)' % (data['tag'], data['mode']), '',
             'Flat world, blocks on y=%d, build area x/z %s-%s, frozen from the first placement to the save. Generated by '
             '`tools/migration/acceptance/oldworld.py generate`; the comparison rules are migration/goal32g-oldworld-criteria.md.'
             % (Y, data['area'][0], data['area'][1]), '',
             'Radiation: gas_meltdown in chunk %s for %s s before the freeze; measured over the 7 x 7 chunks around it.'
             % (data['radiation']['source_chunk'], data.get('rad_seconds')), '', '| Piece | Cells | Why |', '| --- | --- | --- |']
    for pc in data['pieces']:
        first = pc['cells'][0][0] if pc['cells'] else '(entities only)'
        lines.append('| %s | %d from %s | %s |' % (pc['name'], len(pc['cells']), first, pc['why']))
    return '\n'.join(lines) + '\n'


# ---------------------------------------------------------------- helpers

def work_of(args):
    w = common.resolve(args.work).resolve()
    if not str(w).startswith(str((common.REPO / 'build').resolve())):
        raise SystemExit('--work must be under build/')
    return w


def git(*args, binary=False):
    out = subprocess.run(['git', '--no-optional-locks', *args], cwd=common.REPO, check=True, capture_output=True)
    return out.stdout if binary else out.stdout.decode('utf-8')


def blob(ref, path):
    r = subprocess.run(['git', '--no-optional-locks', 'rev-parse', '%s:%s' % (ref, path)], cwd=common.REPO, capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def tool(script, *args):
    return subprocess.run([sys.executable, '-B', '-X', 'utf8', str(Path(__file__).with_name(script)), *args]).returncode


def ps_args(pid):
    return subprocess.run(['ps', '-ww', '-o', 'args=', '-p', str(pid)], capture_output=True, text=True).stdout.strip()


def strip_neo_mods(argv):
    """The dev JVM command line without NEO's own mods: -Dfml.modFolders dropped, build/classes and build/resources of this
    checkout taken off the class path. Raises when anything of this checkout's build output is still passed."""
    out, i = [], 0
    own = (str(common.REPO / 'build' / 'classes'), str(common.REPO / 'build' / 'resources'))
    while i < len(argv):
        a = argv[i]
        if a.startswith('-Dfml.modFolders='):
            i += 1
            continue
        if a in ('-cp', '-classpath', '--class-path') and i + 1 < len(argv):
            kept = [p for p in argv[i + 1].split(':') if not p.startswith(own)]
            out += [a, ':'.join(kept)]
            i += 2
            continue
        out.append(a)
        i += 1
    left = [a for a in out if any(o in a for o in own)]
    if left:
        raise SystemExit('the command line still passes this checkout\'s build output: %s' % [x[:120] for x in left])
    return out


def rcon_client():
    import rcon
    return rcon.connect()


def run_commands(client, commands, transcript):
    replies = []
    for command in commands:
        reply = client.command(command)
        transcript.append('> %s\n%s' % (command, reply or '(no output)'))
        replies.append(reply or '')
    return replies


def wait_loaded(client, points, transcript, timeout=120):
    end = time.time() + timeout
    pending = list(points)
    while pending and time.time() < end:
        pending = [pt for pt in pending if 'passed' not in (client.command('execute if loaded %d %d %d' % pt) or '')]
        if pending:
            time.sleep(1)
    transcript.append('# loaded check: %d of %d points not loaded after the wait%s' % (len(pending), len(points),
                                                                                      ': %s' % pending[:10] if pending else ''))
    return not pending


def session():
    return common.read_json(common.SESSION)


def keep_logs(work, label, server_tag):
    """After a failed start (server.py has stopped and restored already, the session is gone): every log server.py wrote for
    that server tag goes to <work>/logs/."""
    logs = work / 'logs'
    logs.mkdir(parents=True, exist_ok=True)
    kept = []
    for p in sorted((common.STATE / 'logs').glob('server-%s-*' % server_tag)):
        target = logs / ('%s-%s' % (label, p.name))
        shutil.copy2(p, target)
        kept.append(target)
    return kept


def stop_server(work, label):
    """server.py stop (run/ restored), then the session's output logs, complete only now, and the latest.log copy server.py
    keeps go to <work>/logs/ with the label in front. Returns (stop exit code, copied logs, the session as it was)."""
    s = session()
    code = tool('server.py', 'stop')
    logs = work / 'logs'
    logs.mkdir(parents=True, exist_ok=True)
    sources = [Path(x) for x in (s or {}).get('logs', [])]
    if s:
        sources.append(common.STATE / 'logs' / ('server-%s-%s-latest.log' % (s['tag'], s['started'])))
    kept = []
    for p in sources:
        if p.is_file():
            target = logs / ('%s-%s' % (label, p.name))
            shutil.copy2(p, target)
            kept.append(target)
    return code, kept, s


# ---------------------------------------------------------------- path A: the release JAR in the dev environment

def cmd_capture_server(args):
    work = work_of(args)
    s = session()
    if not s or s.get('status') != 'running' or Path(s['root']).resolve() != common.REPO.resolve():
        raise SystemExit('needs a running server.py session of this checkout (server.py start --tag g32g-cap)')
    import server
    pids = server.server_jvms(common.REPO)
    if len(pids) != 1:
        raise SystemExit('expected one dev server JVM, found %s' % pids)
    argv = ps_args(pids[0]).split(' ')
    if not argv or not argv[0].endswith('/java'):
        raise SystemExit('unexpected command line: %s' % argv[:3])
    work.mkdir(parents=True, exist_ok=True)
    common.write_json(work / 'server-argv.json', dict(argv=argv, captured=common.now_tag(), pid=pids[0],
                                                      note='ps -ww -o args= of the runServer JVM; split on single spaces'))
    print('captured %d arguments to %s' % (len(argv), common.rel(work / 'server-argv.json')))
    return 0


def server_argv_source(work, from_client):
    if not from_client:
        captured = common.read_json(work / 'server-argv.json')
        if not captured:
            raise SystemExit('no %s: run capture-server during a dev server session, or pass --from-client'
                             % common.rel(work / 'server-argv.json'))
        return captured['argv'], 'server capture'
    captured = common.read_json(CLIENT_ARGV)
    if not captured:
        raise SystemExit('no %s (client.py capture)' % common.rel(CLIENT_ARGV))
    argv = [a.replace(str(MODDEV / 'clientRunVmArgs.txt'), str(MODDEV / 'serverRunVmArgs.txt'))
             .replace(str(MODDEV / 'clientRunProgramArgs.txt'), str(MODDEV / 'serverRunProgramArgs.txt')) for a in captured['argv']]
    return argv, 'client capture with the server argument files'


def cmd_prepare_jar(args):
    work = work_of(args)
    jar = common.resolve(args.jar).resolve()
    if not jar.is_file():
        raise SystemExit('no JAR at %s' % jar)
    root = work / ('jar-' + args.tag)
    if root.exists():
        raise SystemExit('%s exists; cleanup first' % common.rel(root))
    argv, source = server_argv_source(work, args.from_client)
    argv = strip_neo_mods(argv)
    vm, prog = '@' + str(MODDEV / 'serverRunVmArgs.txt'), '@' + str(MODDEV / 'serverRunProgramArgs.txt')
    if vm not in argv or prog not in argv:
        raise SystemExit('the captured command line does not pass %s and %s' % (vm, prog))
    moddev = root / 'build' / 'moddev'
    moddev.mkdir(parents=True)
    shutil.copy2(MODDEV / 'serverRunVmArgs.txt', moddev / 'serverRunVmArgs.txt')
    lines = (MODDEV / 'serverRunProgramArgs.txt').read_text(encoding='utf-8').splitlines()
    if '--gameDir' not in lines or lines[lines.index('--gameDir') + 1] != '.':
        raise SystemExit('serverRunProgramArgs.txt has no "--gameDir ." (the run directory is the working directory)')
    (moddev / 'serverRunProgramArgs.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    argv = ['@' + str(moddev / 'serverRunVmArgs.txt') if a == vm else '@' + str(moddev / 'serverRunProgramArgs.txt') if a == prog else a
            for a in argv]
    mods = root / 'run' / 'mods'
    mods.mkdir(parents=True)
    shutil.copy2(jar, mods / jar.name)
    record = dict(argv=argv, source=source, jar=common.rel(jar), jar_sha256=common.sha256(jar), tag=args.tag,
                  note='NEO dev server command line without -Dfml.modFolders and without build/classes, build/resources; '
                       'the release JAR in run/mods is the only hbmsntm')
    common.write_json(root / 'launch.json', record)
    print('prepared %s: JAR %s (sha256 %s), %d arguments from the %s' % (common.rel(root), jar.name, record['jar_sha256'][:16],
                                                                       len(argv), source))
    return 0


def ids_at(ref, path, pattern=r'register[A-Za-z]*\("([a-z0-9_]+)"'):
    try:
        text = git('show', '%s:%s' % (ref, path))
    except subprocess.CalledProcessError:
        return set()
    return set(re.findall(pattern, text))


def cmd_trial_jar(args):
    work = work_of(args)
    root = work / ('jar-' + args.tag)
    launch = root / 'launch.json'
    if not launch.is_file():
        raise SystemExit('run prepare-jar first')
    blocks = 'src/main/java/com/hbm/blocks/NtmBlocks.java'
    old_ids, new_ids = ids_at(args.tag, blocks), ids_at('HEAD', blocks)
    absent = sorted(new_ids - old_ids)[:3]
    present = sorted(old_ids & new_ids)[:1]
    tag = 'g32g-trial-' + key_of(args.tag)
    start = time.time()
    code = tool('server.py', 'start', '--tag', tag, '--root', str(root), '--java-argv', str(launch), '--timeout', str(args.timeout))
    result = dict(tag=args.tag, server_tag=tag, start_exit=code, started_s=round(time.time() - start, 1))
    transcript = []
    if code == 0:
        client = rcon_client()
        try:
            for bid in absent + present:
                reply = client.command('setblock 0 %d 0 %s%s' % (Y, H, bid)) or ''
                transcript.append('> setblock %s\n%s' % (bid, reply))
                client.command('setblock 0 %d 0 minecraft:air' % Y)
            result['probes'] = dict(absent_at_tag=absent, present=present)
        finally:
            client.close()
    s = session()
    if s:
        code_stop, logs, s = stop_server(work, 'trial-' + args.tag)
        result['stop_exit'] = code_stop
        tool('server.py', 'delete-world', '--tag', tag, '--root', str(root))
    else:
        logs = []
    text = '\n'.join(Path(p).read_text(encoding='utf-8', errors='replace') for p in logs if Path(p).suffix == '.log')
    jar_name = Path(common.read_json(launch)['jar']).name
    result.update(log_mentions_jar=jar_name in text, log_mentions_neo_classes=str(common.REPO / 'build' / 'classes') in text,
                  transcript=transcript, logs=[common.rel(p) for p in logs])
    unknown = [t for t in transcript[:len(absent)] if 'nknown' in t]
    result['unknown_replies'] = len(unknown)
    # Decisive when the tag lacks blocks the current tree has: the server must not know them. Otherwise only the log names the JAR.
    proof = (len(unknown) == len(absent)) if absent else result['log_mentions_jar']
    result['verdict'] = 'works' if code == 0 and proof and not result['log_mentions_neo_classes'] else 'does not work'
    common.write_json(work / ('trial-%s.json' % args.tag), result)
    (work / 'logs').mkdir(parents=True, exist_ok=True)
    (work / 'logs' / ('trial-%s-rcon.txt' % args.tag)).write_text('\n'.join(transcript) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k != 'transcript'}, indent=1))
    return 0 if result['verdict'] == 'works' else 1


def cmd_prepare_client(args):
    """An old-version dev client: the captured client command line without NEO's mods, the release JAR in the client's own
    mods folder (build/migration/accept/clients/<name>/mods), started by client.py start --argv."""
    work = work_of(args)
    launch = common.read_json(work / ('jar-' + args.tag) / 'launch.json')
    if not launch:
        raise SystemExit('run prepare-jar for %s first' % args.tag)
    captured = common.read_json(CLIENT_ARGV)
    if not captured:
        raise SystemExit('no %s (client.py capture)' % common.rel(CLIENT_ARGV))
    argv = strip_neo_mods(captured['argv'])
    target = work / ('client-argv-%s.json' % args.tag)
    common.write_json(target, dict(argv=argv, captured=captured.get('captured'), note='client-argv.json without NEO mods (oldworld.py)'))
    mods = common.CLIENTS / args.name / 'mods'
    if mods.exists() and any(mods.iterdir()):
        raise SystemExit('%s is not empty' % common.rel(mods))
    mods.mkdir(parents=True, exist_ok=True)
    jar = common.resolve(launch['jar'])
    shutil.copy2(jar, mods / jar.name)
    common.write_json(work / ('client-%s.json' % args.tag), dict(name=args.name, argv=common.rel(target), mods=[common.rel(mods / jar.name)]))
    print('client %s: argv %s, JAR in %s' % (args.name, common.rel(target), common.rel(mods)))
    return 0


def remove_client_jar(work, tag):
    rec = common.read_json(work / ('client-%s.json' % tag))
    if not rec:
        return
    for f in rec['mods']:
        p = common.resolve(f)
        if p.is_file():
            p.unlink()
    mods = common.CLIENTS / rec['name'] / 'mods'
    if mods.is_dir() and not any(mods.iterdir()):
        mods.rmdir()


# ---------------------------------------------------------------- path B: the tag's source tree

def cmd_extract(args):
    work = work_of(args)
    tree = work / ('src-' + args.tag)
    if tree.exists():
        raise SystemExit('%s exists; run cleanup first' % common.rel(tree))
    commit = git('rev-parse', args.tag + '^{commit}').strip()
    same = {f: blob(args.tag, f) == blob('HEAD', f) for f in BUILD_FILES}
    lock_re = re.compile(r'^([^#=\s]+:[^=\s]+:[^=\s]+)=', re.M)
    old_lock = set(lock_re.findall(git('show', '%s:gradle.lockfile' % args.tag)))
    new_lock = set(lock_re.findall(git('show', 'HEAD:gradle.lockfile')))
    data = git('archive', '--format=tar', args.tag, binary=True)
    tree.mkdir(parents=True)
    with tarfile.open(fileobj=io.BytesIO(data)) as tar:
        tar.extractall(tree, filter='data')
    gradle = tree / 'build.gradle'
    text = gradle.read_text(encoding='utf-8')
    patched = False
    if 'java-objc-bridge' not in text:
        if text.count(LOCK_ANCHOR) != 1:
            raise SystemExit('build.gradle has no java-objc-bridge ignore line and the anchor is not there exactly once')
        gradle.write_text(text.replace(LOCK_ANCHOR, LOCK_ANCHOR + LOCK_LINES), encoding='utf-8')
        patched = True
    build_sh = tree / 'tools' / 'migration' / 'build.sh'
    copied = False
    if not build_sh.is_file():
        build_sh.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(common.BUILD_SH, build_sh)
        copied = True
    files = sum(1 for p in tree.rglob('*') if p.is_file())
    record = dict(tag=args.tag, commit=commit, files=files, build_files_same_as_head=same,
                  lock_coordinates_not_in_head=sorted(old_lock - new_lock), objc_line_patched=patched, build_sh_copied=copied,
                  build_gradle_sha256=common.sha256(gradle), fluids_same_as_head=blob(args.tag, FLUIDS_JAVA) == blob('HEAD', FLUIDS_JAVA))
    common.write_json(work / ('extract-%s.json' % args.tag), record)
    print(json.dumps(record, indent=1))
    if record['lock_coordinates_not_in_head']:
        print('warning: dependencies the current lock file does not list; the offline build may stop on them ("no runtime")')
    return 0


# ---------------------------------------------------------------- generate, load, compare

def cmd_plan(args):
    p = plan(args.tag)
    for line in build_commands(p) + readback_commands(p):
        print(line)
    print('# %d pieces, %d cells, %d probes' % (len(p['pieces']), sum(len(pc['cells']) for pc in p['pieces']), len(probes(p))),
          file=sys.stderr)
    return 0


def cmd_generate(args):
    work = work_of(args)
    world_dir = work / ('world-' + args.tag)
    if world_dir.exists():
        raise SystemExit('%s exists' % common.rel(world_dir))
    if blob(args.tag, FLUIDS_JAVA) != blob('HEAD', FLUIDS_JAVA):
        raise SystemExit('Fluids.java differs between %s and HEAD: the numeric fluid IDs of the plan would be wrong' % args.tag)
    p = plan(args.tag)
    stag = 'g32g-gen-' + key_of(args.tag)
    if args.mode == 'jar':
        root = work / ('jar-' + args.tag)
        extra_start = ['--java-argv', str(root / 'launch.json')]
        source = dict(jar=common.read_json(root / 'launch.json')['jar'], jar_sha256=common.read_json(root / 'launch.json')['jar_sha256'])
    else:
        root = work / ('src-' + args.tag)
        extra_start = []
        source = dict(commit=git('rev-parse', args.tag + '^{commit}').strip())
    if not root.is_dir():
        raise SystemExit('no %s: prepare-jar or extract first' % common.rel(root))
    t0 = time.time()
    code = tool('server.py', 'start', '--tag', stag, '--root', str(root), '--timeout', str(args.timeout), *extra_start)
    if code != 0:
        # server.py has already stopped what it started and restored the root's run/.
        keep_logs(work, 'gen-' + args.tag, stag)
        print('old server did not start (see %s/logs); for path B record "no runtime" when a dependency is missing' % common.rel(work))
        return 1
    started = time.time()
    transcript = ['# server start %.0f s' % (started - t0)]
    s = session()
    world = Path(s['world'])
    client = rcon_client()
    try:
        run_commands(client, ['gamerule doDaylightCycle false', 'gamerule doWeatherCycle false', 'gamerule doMobSpawning false',
                              'time set 6000', 'weather clear', 'tick unfreeze'] +
                     ['forceload add %d %d %d %d' % box for box in forceload_boxes(p)], transcript)
        rc = p['radiation']['source_chunk']
        wait_loaded(client, [(rc[0] * 16 + 8, Y, rc[1] * 16 + 8)] + [(c[0] * 16 + 8, Y, c[1] * 16 + 8) for c in p['area_chunks']], transcript)
        (g0, g1) = p['radiation']['gas']
        run_commands(client, ['fill %d %d %d %d %d %d %sgas_meltdown' % (*g0, *g1, H)], transcript)
        time.sleep(args.rad_seconds)
        run_commands(client, ['tick freeze'] + ['fill %d %d %d %d %d %d minecraft:air replace %s%s' % (*RAD_CLEAN[0], *RAD_CLEAN[1], H, gas)
                                                for gas in ('gas_meltdown', 'gas_radon_dense', 'gas_radon')], transcript)
        build_start = time.time()
        run_commands(client, build_commands(p), transcript)
        if args.player:
            transcript.append('# player %s' % args.player)
            client.close()
            joined = tool('client.py', 'start', args.player, '--server', '%s:%d' % (common.LOOPBACK, s['port']), '--wait-join',
                          '--argv', str(work / ('client-argv-%s.json' % args.tag)), '--mute') == 0
            client = rcon_client()
            if joined:
                run_commands(client, ['ntmprops set %s radiation 77.5' % args.player, 'ntmprops set %s asbestos 30' % args.player,
                                      'give %s %srod_zirnox[%smeta=2] 1' % (args.player, H, H), 'give %s %singot_steel 7' % (args.player, H)],
                             transcript)
                time.sleep(3)
                client.close()
                tool('client.py', 'stop', args.player)
                client = rcon_client()
            else:
                transcript.append('# the old client did not join; player data not covered')
        run_commands(client, readback_commands(p), transcript)
        # `forceload remove all` can leave a chunk forced (seen in the first generation run: one chunk of the radiation box
        # stayed in data/chunks.dat), so every box is also removed explicitly and the query is kept in the transcript.
        run_commands(client, ['forceload remove all'] + ['forceload remove %d %d %d %d' % box for box in forceload_boxes(p)] +
                     ['forceload query', 'save-all flush'], transcript)
        transcript.append('# build and read-back %.0f s' % (time.time() - build_start))
    finally:
        client.close()
    (work / 'logs').mkdir(parents=True, exist_ok=True)
    (work / 'logs' / ('gen-%s-rcon.txt' % args.tag)).write_text('\n'.join(transcript) + '\n', encoding='utf-8')
    stopped, logs, s = stop_server(work, 'gen-' + args.tag)
    import server as server_module
    if stopped != 0 or server_module.server_jvms(root) or session():
        raise SystemExit('the old server did not stop cleanly (exit %d); the world stays at %s' % (stopped, world))
    if not world.is_dir():
        raise SystemExit('world not found after stop: %s' % world)
    shutil.move(str(world), str(world_dir))
    (world_dir / 'session.lock').unlink(missing_ok=True)
    server_module.register_world(world, stag, 'moved to ' + common.rel(world_dir))
    data = placed_json(p, args.tag, args.mode, dict(source=source, server_tag=stag, rad_seconds=args.rad_seconds,
                                                     player=args.player, generated=common.now_tag(),
                                                     wall_s=round(time.time() - t0, 1), logs=[common.rel(x) for x in logs],
                                                     rcon=common.rel(work / 'logs' / ('gen-%s-rcon.txt' % args.tag))))
    common.write_json(world_dir / 'placed.json', data)
    (world_dir / 'PLACED.md').write_text(placed_md(data), encoding='utf-8')
    print('kept the old world at %s (%.0f s wall)' % (common.rel(world_dir), time.time() - t0))
    return 0


def value_of(reply):
    m = re.search(r'has the following (?:block|entity) data: (.*)$', reply or '', re.S)
    return m.group(1).strip() if m else None


def number(reply):
    v = value_of(reply)
    m = re.match(r'(-?[\d.]+(?:E-?\d+)?)[bsLfd]?$', v or '')
    return float(m.group(1)) if m else None


def item_counts(reply):
    counts = {}
    for entry in re.findall(r'\{[^{}]*\}', value_of(reply) or ''):
        iid = re.search(r'id: "([^"]+)"', entry)
        cnt = re.search(r'count: (\d+)', entry)
        if iid:
            counts[iid.group(1)] = counts.get(iid.group(1), 0) + (int(cnt.group(1)) if cnt else 1)
    return counts


def functional_checks(client, p, transcript):
    """F1-F4 (criteria): readings before, 100 ticks of `tick step`, readings after; the world stays frozen around it."""
    f = p['functional']
    before, after = {}, {}

    def read(store):
        for fid, spec in f.items():
            if spec['kind'] == 'increase':
                r = client.command('data get block %d %d %d %s' % (*spec['pos'], spec['path']))
                transcript.append('> %s %s\n%s' % (fid, spec['path'], r))
                store[fid] = number(r)
            elif spec['kind'] == 'moved':
                r = client.command('data get entity %s' % spec['selector'])
                transcript.append('> %s entity\n%s' % (fid, r))
                pos = re.search(r'Pos: \[(-?[\d.]+)d, (-?[\d.]+)d, (-?[\d.]+)d\]', r or '')
                itm = re.search(r'Item: \{[^{}]*id: "([^"]+)"[^{}]*\}', r or '') or re.search(r'id: "(minecraft:[^"]+)"', r or '')
                cnt = re.search(r'count: (\d+)', r or '')
                store[fid] = dict(pos=[float(x) for x in pos.groups()] if pos else None, item=itm.group(1) if itm else None,
                                  count=int(cnt.group(1)) if cnt else None)
            elif spec['kind'] == 'filter':
                r = client.command('data get block %d %d %d Items' % tuple(spec['chest']))
                transcript.append('> %s chest\n%s' % (fid, r))
                store[fid] = item_counts(r)

    read(before)
    transcript.append('> tick step 100\n%s' % client.command('tick step 100'))
    time.sleep(8)
    transcript.append('> tick query\n%s' % client.command('tick query'))
    read(after)
    checks = {}
    for fid, spec in f.items():
        b, a = before.get(fid), after.get(fid)
        if spec['kind'] == 'increase':
            ok = b is not None and a is not None and a > b
        elif spec['kind'] == 'moved':
            ok = bool(b and a and b['pos'] and a['pos'] and a['pos'] != b['pos'] and a['item'] == b['item'] and a['count'] == b['count'])
        else:
            ok = bool(b and a and a.get(spec['take'], 0) < b.get(spec['take'], 0) and a.get(spec['keep'], 0) == b.get(spec['keep'], 0)
                      and b.get(spec['keep'], 0) > 0)
        checks[fid] = dict(verdict='pass' if ok else ('not-run' if b is None else 'fail'), before=b, after=a, spec=spec)
    return checks


def cmd_load(args):
    work = work_of(args)
    world_dir = work / ('world-' + args.tag)
    placed = common.read_json(world_dir / 'placed.json')
    if not placed:
        raise SystemExit('no %s' % common.rel(world_dir / 'placed.json'))
    loaded = work / ('loaded-' + args.tag)
    if loaded.exists():
        raise SystemExit('%s exists' % common.rel(loaded))
    stag = 'g32g-load-' + key_of(args.tag)
    t0 = time.time()
    if tool('server.py', 'start', '--tag', stag, '--from-world', str(world_dir), '--timeout', str(args.timeout)) != 0:
        keep_logs(work, 'load-' + args.tag, stag)
        return 1
    transcript = ['# server start %.0f s' % (time.time() - t0)]
    p = dict(placed, functional=placed['functional'])
    s = session()
    world = Path(s['world'])
    result = dict(tag=args.tag, server_tag=stag)
    client = rcon_client()
    try:
        run_commands(client, ['tick freeze'], transcript)

        def dirty(chunks):
            # y = -63 is dirt in the flat preset; changing it and back marks the chunk unsaved, so the save rewrites every block entity.
            return [c for cx, cz in chunks for c in ('setblock %d -63 %d minecraft:coarse_dirt' % (cx * 16, cz * 16),
                                                     'setblock %d -63 %d minecraft:dirt' % (cx * 16, cz * 16))]

        area_box, rad_box = forceload_boxes(placed)
        # The build area first; the radiation chunks last and saved at once: chunk radiation keeps spreading and decaying
        # while frozen (criteria R1), so its window runs from their forceload to the end of the save.
        run_commands(client, ['forceload add %d %d %d %d' % area_box], transcript)
        area_loaded = wait_loaded(client, sorted(set(tuple(pos) for pc in placed['pieces'] for pos, state in pc['cells'])), transcript)
        run_commands(client, dirty([tuple(c) for c in placed['area_chunks']]), transcript)
        w0 = time.time()
        run_commands(client, ['forceload add %d %d %d %d' % rad_box], transcript)
        rad_loaded = wait_loaded(client, [(c[0] * 16 + 8, Y, c[1] * 16 + 8) for c in placed['radiation']['chunks']], transcript)
        result['all_loaded'] = area_loaded and rad_loaded
        run_commands(client, dirty([tuple(c) for c in placed['radiation']['chunks']]), transcript)
        run_commands(client, ['save-off', 'save-all flush'], transcript)
        result['radiation_window_s'] = round(time.time() - w0, 1)
        shutil.copytree(world, loaded, ignore=shutil.ignore_patterns('session.lock'))
        run_commands(client, ['save-on'], transcript)
        run_commands(client, ['data get block %d %d %d' % tuple(pos) for pos in [i['pos'] for i in placed['injected']]], transcript)
        if args.player:
            client.close()
            remove_client_jar(work, args.tag)
            joined = tool('client.py', 'start', args.player, '--server', '%s:%d' % (common.LOOPBACK, s['port']), '--wait-join', '--mute') == 0
            result['player_joined'] = joined
            time.sleep(3)
            tool('client.py', 'stop', args.player)
            client = rcon_client()
            run_commands(client, ['save-all flush'], transcript)
            src = world / 'playerdata'
            if src.is_dir():
                (loaded / 'playerdata').mkdir(exist_ok=True)
                for f in src.glob('*.dat'):
                    shutil.copy2(f, loaded / 'playerdata' / f.name)
        result['checks'] = functional_checks(client, p, transcript)
    finally:
        client.close()
    (work / 'logs').mkdir(parents=True, exist_ok=True)
    (work / 'logs' / ('load-%s-rcon.txt' % args.tag)).write_text('\n'.join(transcript) + '\n', encoding='utf-8')
    stopped, logs, s = stop_server(work, 'load-' + args.tag)
    tool('server.py', 'delete-world', '--tag', stag)
    result.update(stop_exit=stopped, logs=[common.rel(x) for x in logs], wall_s=round(time.time() - t0, 1),
                  loaded=common.rel(loaded), rcon=common.rel(work / 'logs' / ('load-%s-rcon.txt' % args.tag)))
    common.write_json(work / ('functional-%s.json' % args.tag), result)
    print(json.dumps({k: v for k, v in result.items() if k != 'checks'}, indent=1))
    print({k: c['verdict'] for k, c in result['checks'].items()})
    return 0 if stopped == 0 else 1


def cmd_control(args):
    """The current build on a fresh flat world with the load steps (freeze, chunk tickets, unsaved marks, save): its log is the
    control log of criteria L1."""
    work = work_of(args)
    stag = 'g32g-control'
    t0 = time.time()
    if tool('server.py', 'start', '--tag', stag, '--timeout', str(args.timeout)) != 0:
        keep_logs(work, 'control', stag)
        return 1
    p = plan('v0.31.0')
    transcript = []
    client = rcon_client()
    try:
        run_commands(client, ['tick freeze'] + ['forceload add %d %d %d %d' % box for box in forceload_boxes(p)], transcript)
        wait_loaded(client, [(c[0] * 16 + 8, Y, c[1] * 16 + 8) for c in p['area_chunks']], transcript)
        run_commands(client, ['save-off', 'save-all flush', 'save-on'], transcript)
    finally:
        client.close()
    stopped, logs, s = stop_server(work, 'control')
    tool('server.py', 'delete-world', '--tag', stag)
    out = [x for x in logs if x.name.startswith('control-server-') and not x.name.endswith('-latest.log') and x.suffix == '.log']
    common.write_json(work / 'control.json', dict(stop_exit=stopped, logs=[common.rel(x) for x in logs], wall_s=round(time.time() - t0, 1),
                                                  control_log=common.rel(out[-1]) if out else None))
    print('control log: %s' % (common.rel(out[-1]) if out else None))
    return 0 if stopped == 0 else 1


def cmd_compare(args):
    work = work_of(args)
    old = work / ('world-' + args.tag)
    new = work / ('loaded-' + args.tag)
    placed = common.read_json(old / 'placed.json')
    functional = common.read_json(work / ('functional-%s.json' % args.tag))
    if not placed or not functional or not new.is_dir():
        raise SystemExit('generate and load %s first' % args.tag)
    logs = [common.resolve(x) for x in functional['logs'] if x.endswith('.log') and not x.endswith('-latest.log')]
    log_text = '\n'.join(p.read_text(encoding='utf-8', errors='replace') for p in logs if p.is_file()) if logs else None
    control = common.resolve(args.control_log).read_text(encoding='utf-8', errors='replace') if args.control_log else None
    result = oc.compare(old, new, placed, log_text, control, functional)
    result.update(tag=args.tag, logs=[common.rel(p) for p in logs], control_log=args.control_log,
                  criteria_sha256=common.sha256(common.REPO / 'migration' / 'goal32g-oldworld-criteria.md'))
    out = work / ('compare-%s' % args.tag)
    # Not with_suffix: the tag's last dot would be taken for the suffix (compare-v0.30.json).
    common.write_json(Path(str(out) + '.json'), result)
    Path(str(out) + '.md').write_text(oc.markdown(result, 'Old-world comparison %s' % args.tag), encoding='utf-8')
    print('%s: %s (%s.json/.md)' % (args.tag, result['counts'], common.rel(out)))
    return 1 if any(c['verdict'] == 'fail' for c in result['checks'].values()) else 0


# ---------------------------------------------------------------- fixtures and cleanup

def cmd_fixture(args):
    work = work_of(args)
    world_dir = work / ('world-' + args.tag)
    if not (world_dir / 'level.dat').is_file():
        raise SystemExit('no world at %s' % common.rel(world_dir))
    if not re.fullmatch(r'v[\d.]+-goal32g-oldworld\.zip', args.name):
        raise SystemExit('--name like v0.30-goal32g-oldworld.zip')
    target = common.REPO / 'migration' / 'fixtures' / args.name
    if target.exists():
        raise SystemExit('%s exists' % common.rel(target))
    top = 'g32g-oldworld-' + args.tag
    with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for f in sorted(p for p in world_dir.rglob('*') if p.is_file() and p.name != 'session.lock'):
            info = zipfile.ZipInfo('%s/%s' % (top, f.relative_to(world_dir).as_posix()), date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, f.read_bytes())
    digest = common.sha256(target)
    placed = common.read_json(world_dir / 'placed.json')
    common.write_json(work / ('fixture-%s.json' % args.tag), dict(zip=common.rel(target), sha256=digest, top=top))
    print('%s sha256 %s' % (common.rel(target), digest))
    print('README entry inputs: world %s, %s %s, generated %s, rcon %s' % (top, placed['mode'], placed.get('source'),
                                                                           placed.get('generated'), placed.get('rcon')))
    return 0


def cmd_cleanup(args):
    work = work_of(args)
    if session():
        raise SystemExit('a server session is open; stop it first')
    removed = []
    for name in ('src-' + args.tag, 'jar-' + args.tag):
        root = work / name
        if root.is_dir() and not root.is_symlink() and root.parent.resolve() == work:
            logs = root / 'run' / 'logs'
            if logs.is_dir():
                shutil.copytree(logs, work / 'logs' / ('%s-runlogs' % name), dirs_exist_ok=True)
            shutil.rmtree(root)
            removed.append(name)
    remove_client_jar(work, args.tag)
    if args.worlds:
        fixture = common.read_json(work / ('fixture-%s.json' % args.tag))
        if not fixture or not common.resolve(fixture['zip']).is_file():
            raise SystemExit('no fixture zip recorded for %s; refusing to delete the worlds' % args.tag)
        for name in ('world-' + args.tag, 'loaded-' + args.tag):
            if (work / name).is_dir():
                shutil.rmtree(work / name)
                removed.append(name)
    print('removed %s; logs kept in %s' % (removed or 'nothing', common.rel(work / 'logs')))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--work', default=str(DEFAULT_WORK), help='working directory under build/ (default %(default)s)')
    sub = ap.add_subparsers(dest='command', required=True)
    sub.add_parser('capture-server').set_defaults(func=cmd_capture_server)
    p = sub.add_parser('prepare-jar')
    p.add_argument('--tag', required=True)
    p.add_argument('--jar', required=True)
    p.add_argument('--from-client', action='store_true', help='derive the server command line from client-argv.json')
    p.set_defaults(func=cmd_prepare_jar)
    p = sub.add_parser('trial-jar')
    p.add_argument('--tag', required=True)
    p.add_argument('--timeout', type=int, default=900)
    p.set_defaults(func=cmd_trial_jar)
    p = sub.add_parser('prepare-client')
    p.add_argument('--tag', required=True)
    p.add_argument('--name', required=True)
    p.set_defaults(func=cmd_prepare_client)
    p = sub.add_parser('extract')
    p.add_argument('--tag', required=True)
    p.set_defaults(func=cmd_extract)
    p = sub.add_parser('plan')
    p.add_argument('--tag', required=True)
    p.set_defaults(func=cmd_plan)
    p = sub.add_parser('generate')
    p.add_argument('--tag', required=True)
    p.add_argument('--mode', choices=('jar', 'source'), required=True)
    p.add_argument('--player', help='an old-version client joins (prepare-client first; path A only)')
    p.add_argument('--rad-seconds', type=int, default=20, help='wall seconds the gas runs before the freeze')
    p.add_argument('--timeout', type=int, default=2400, help='seconds for the server to reach Done (path B compiles)')
    p.set_defaults(func=cmd_generate)
    p = sub.add_parser('load')
    p.add_argument('--tag', required=True)
    p.add_argument('--player', help='the same player joins the current build (its old-version JAR is removed first)')
    p.add_argument('--timeout', type=int, default=1200)
    p.set_defaults(func=cmd_load)
    p = sub.add_parser('control')
    p.add_argument('--timeout', type=int, default=1200)
    p.set_defaults(func=cmd_control)
    p = sub.add_parser('compare')
    p.add_argument('--tag', required=True)
    p.add_argument('--control-log')
    p.set_defaults(func=cmd_compare)
    p = sub.add_parser('fixture')
    p.add_argument('--tag', required=True)
    p.add_argument('--name', required=True)
    p.set_defaults(func=cmd_fixture)
    p = sub.add_parser('cleanup')
    p.add_argument('--tag', required=True)
    p.add_argument('--worlds', action='store_true', help='also delete world-<tag> and loaded-<tag> (needs the fixture zip)')
    p.set_defaults(func=cmd_cleanup)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
