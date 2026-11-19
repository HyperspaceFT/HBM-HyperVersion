"""Dedicated server: the large radar's first map scan reads only chunks already saved and creates no region files.

Layout (flat world): A places a large radar by hand on a stone platform at y = 60 (the radar screen opens only at y >= 55); its
core is found from the placed blocks. The map
covers the square of +-RANGE blocks around the core in 200 x 200 cells; cell (iX, iZ) is the world column
x = core x - RANGE + iX * RANGE * 2 / 200, z = core z - RANGE + iZ * RANGE * 2 / 200 (index iZ * 200 + iX).
Three stone pillars (command) stand exactly on the columns of three cells 2,970-3,000 blocks west of the core, in chunks that are
force-loaded only to build them and then unloaded, so they are saved on disk and not loaded when the scan starts. Force-loading a
chunk also saves the partly generated chunks around it, and each saved chunk the scan meets costs one of the 10 loads a tick, so
the pillars are the first cells of their tick's slice. A cell 1,800 blocks west and 300 south lies in a region never generated.
Cells that the cap leaves at 0 in one sweep are tried again in the next (NEO MachineRadarBlockEntity.java:136-138,155), so the
map is not complete after the first sweep wherever more than 10 saved chunks fall into one slice.

Expected (original 1.7.10 TileEntityMachineRadarNT / WorldUtil; NEO MachineRadarBlockEntity, MachineRadarLargeBlockEntity):
- range 3,000 for the large radar (original TileEntityMachineRadarLarge.java:15,33-35; NEO
  MachineRadarLargeBlockEntity.java:16,23-25), so a cell is 30 blocks; 100 cells a tick, index = (game time mod 400) * 100 + i,
  so one sweep over all 40,000 cells takes exactly 400 ticks (original TileEntityMachineRadarNT.java:179-184; NEO
  MachineRadarBlockEntity.java:140-150);
- a loaded chunk's cell is its height clamped to 50..128; an unloaded cell still 0 that lies in a chunk saved on disk is loaded
  from disk without generating it, at most chunkLoadCap = 10 loads a tick (original TileEntityMachineRadarNT.java:99; NEO
  MachineRadarBlockEntity.java:82), and drawn as its height (the top block + 1, clamped);
  a chunk that is not on disk is not requested and its cell is written 50 (original TileEntityMachineRadarNT.java:189-201,
  WorldUtil.java:129-155; NEO MachineRadarBlockEntity.java:152-175, 197-235). A pillar whose top block is at y = T is drawn T + 1.
- nothing in the scan creates a region file: the original asks the chunk loader whether the chunk exists before loading
  (WorldUtil.java:142-150); NEO reads the region header read-only (MachineRadarBlockEntity.java:212-235).
- the map is synced to players within 50 blocks one 100-cell slice a tick (NEO MachineRadarBlockEntity.java:181,265-280), so
  after one sweep the client's copy holds every cell, the pillars included.
- the map is saved with the block entity (NEO MachineRadarBlockEntity.java:326,340). The restart row also records the save time
  of the radar's own chunk from its region header (the second 4 KiB sector holds one big-endian epoch-second stamp per chunk,
  vanilla RegionFile's layout), read right after the save before the scan and again after the restart: an unchanged stamp
  means the server did not write that chunk again when it stopped. It also records the radar's "showMap" and "map" as stored in
  that chunk on disk after the restart, so a loss shows whether the save or the load dropped them.
- a region file whose header cannot be read counts as holding no chunk: its cells are written 50 without a load and without
  counting toward the cap (NEO MachineRadarBlockEntity.java:202-239, readSavedChunks). The original asks the chunk loader
  (WorldUtil.java:140-155), whose 1.7.10 RegionFile catches the failed open and keeps an all-zero offset table, so chunkExists is
  false, nothing is loaded and the cell is getHeightValue of an unloaded chunk, 0, clamped to 50 (TileEntityMachineRadarNT.java:194-197).
  A fourth pillar stands in a region of its own; that file is made unreadable (file mode 000, the world is disposable) after it is
  saved and before the map is switched on, and its old mode is put back after the first sweep. A fifth pillar in a third region,
  drawn in the first sweep, is the control that a readable saved pillar of the same kind is drawn.
- a chunk file deleted while the server runs: NEO caches each region header for the rest of the 400-tick sweep (:136-138,202-206),
  so a header read before the deletion still says the chunk is saved and the cell asks the server for the chunk at status EMPTY
  (:161-169), which never generates terrain. The original loads a chunk only when the chunk loader says it exists and never
  generates one (WorldUtil.java:129-155). After the restart (the server has not opened the fifth pillar's region since), the map is
  cleared in a frozen world, the world is stepped to the tick in which the radar reaches the region's first cell (it reads the
  header there and writes that cell 50), the region file is deleted from disk, and the world is stepped to the pillar's tick. The
  pillar cell may be 50 (no chunk found) or its height (old data through a file the server still holds open); a save afterwards must
  leave no chunk in a file at that path: nothing was generated or written for the deleted region.
"""
import importlib.util
import os
import stat
import struct
import sys
import time
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _lib  # noqa: E402
import common  # noqa: E402

_spec = importlib.util.spec_from_file_location('zirnox_mp_rig', Path(__file__).resolve().parents[1] / 'zirnox-reactor' / 'mp_meltdown.py')
Z = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(Z)

SCENARIO = dict(
    id='radar.mp_first_scan',
    feature='radar',
    title='Dedicated server: large radar first map scan (lag, region files, saved chunks drawn, map kept over a restart)',
    group='mp',
    capture=dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70),
)

G = _lib.FLAT_FEET
H = _lib.H
SITE = (-60, 40)
PLATFORM = 60                    # platform block y; the radar and the players stand on y = 61
FEET = PLATFORM + 1
RANGE = 3000                     # MachineRadarLargeBlockEntity.java:16
SWEEP = 400                      # 40,000 cells / 100 a tick
# (iX, iZ, top block y): the first cells of their tick's 100-cell slice (index iZ * 200 + iX, slice index // 100), so at most one
# saved chunk is loaded before them in that tick and the cap of 10 loads cannot hold them back in the first sweep
PILLARS = [(0, 100, 60), (1, 100, 80), (0, 102, 100)]
UNSAVED = (60, 110)              # 1,800 blocks west and 300 south of the core: a region never generated
GUI_W, GUI_H = 216, 234          # MachineRadarScreen.java:33-34
MAP_BUTTON = (-10 + 4, 138 + 4)  # MachineRadarScreen.java:64 ("map": 8 x 8 at -10, 138)
CLEAR_BUTTON = (-10 + 4, 178 + 4)  # MachineRadarScreen.java:66 ("clear": 8 x 8 at -10, 178; original GUIMachineRadarNT.java:60)
HEADER_TOP = 70                  # the pillar in the unreadable region
DELETED_TOP = 90                 # the pillar in the region deleted while running (and the readable control of the first sweep)
RD = 'radar.'
EXPECT = [
    ('mp-first-scan-lag', '专服首轮扫描（大型雷达，40,000 格每刻 100 格，正好 400 刻）期间服务端不落后：开地图前读的游戏时刻起走满 400 刻所用的墙钟，'
     '减去 400 刻应有的 20 秒，差不超过 1 秒（0.5 秒一次的 RCON 轮询的粒度）；修正前的实测是落后约 18.5 秒',
     'TileEntityMachineRadarNT.java:179-201; MachineRadarBlockEntity.java:140-175'),
    ('mp-first-scan-files', '专服首轮扫描前后数世界的 region 目录：文件名的集合不变、没有 0 字节文件、从未生成的西面区域没有文件（修正前的实测是多出 160 个 0 字节文件）；'
     'poi 与 entities 目录的新文件一并记录',
     'WorldUtil.java:129-155; MachineRadarBlockEntity.java:197-235'),
    ('mp-first-scan-drawn', '首轮之后：三根石柱（顶块 y=60、80、100，所在区块扫描前已存盘、未加载，各在自己那一刻 100 格的第 1、2 格，前面至多 1 次读盘，'
     '不受每刻 10 次的上限）的格子在服务端是 61、81、101；从未生成的格子是 50；A、B 两个客户端的地图副本里这几格与服务端相同（因上限留到下一轮的 0 格数只记录）',
     'TileEntityMachineRadarNT.java:189-201; MachineRadarBlockEntity.java:152-175,265-280'),
    ('mp-first-scan-header-read-error', '专服：读区域文件头出错时整个区域当没有存盘：第四根石柱（顶块 y=70）单独占一个区域文件，所在区块扫描前已存盘（文件头里有它的条目）、'
     '未加载；开地图前把这个区域文件改成不可读（文件权限 000，世界是一次性的），首轮扫描之后服务端与 A、B 两个客户端的地图里这一格都是 50'
     '（不读盘、不计入每刻 10 次的上限），服务端照常运行；扫描后改回原来的权限。对照：同一轮里另一个可读区域的第五根石柱（顶块 y=90）画成 91。'
     '原版问区块加载器，1.7.10 的 RegionFile 打开失败时吞掉异常、偏移表全 0，chunkExists 为假，不加载，未加载区块的高度 0 夹到 50',
     'TileEntityMachineRadarNT.java:189-201, WorldUtil.java:140-155; MachineRadarBlockEntity.java:152-175,202-239'),
    ('mp-first-scan-chunk-file-deleted', '专服：运行中区块文件被删除不会生成区块：重启之后（服务端还没打开过第五根石柱所在的区域文件），冻结世界里 A 在雷达界面点清图，'
     '世界一刻一刻走到雷达扫到这个区域第一格的那一刻（雷达在这一刻读文件头并缓存到这一轮结束，这一格写成 50 证明读过），随即从磁盘删掉这个区域文件，'
     '再走到石柱那一格被扫的那一刻：石柱格是 50（盘上已没有数据，只按 EMPTY 状态取区块，不生成地形）或 91（服务端仍开着旧文件读到旧数据）；'
     '之后存盘（save-all），这个路径上要么没有文件，要么文件头里一个区块条目都没有：没有为被删的区域生成或写入区块。原版只在区块加载器说区块存在时才加载、从不生成',
     'TileEntityMachineRadarNT.java:189-201, WorldUtil.java:129-155; MachineRadarBlockEntity.java:136-138,152-175,185-189,202-206,457'),
    ('mp-first-scan-restart', '专服重启后比对静止的服务端读数：地图开关与三根石柱、未生成格子的地图值与重启前相同',
     'MachineRadarBlockEntity.java:316-340'),
]


def expectations():
    return [dict(id=RD + k, text=t, source=s) for k, t, s in EXPECT]


def cell_pos(core, ix, iz):
    return core[0] - RANGE + ix * RANGE * 2 // 200, core[2] - RANGE + iz * RANGE * 2 // 200


def index(ix, iz):
    return iz * 200 + ix


def world_dir():
    session = common.read_json(common.SESSION) or {}
    return Path(session['world'])


def listing():
    """{dir/name: size} of the region, poi and entities files of the overworld."""
    out = {}
    for sub in ('region', 'poi', 'entities'):
        d = world_dir() / sub
        if d.is_dir():
            for f in sorted(d.iterdir()):
                out['%s/%s' % (sub, f.name)] = f.stat().st_size
    return out


def region_file(cx, cz):
    return world_dir() / 'region' / ('r.%d.%d.mca' % (cx >> 5, cz >> 5))


def disposable(path):
    """Refuses any file change outside the disposable accept- world server.py created under run/."""
    w = world_dir().resolve()
    if not w.name.startswith('accept-') or w.parent.name != 'run' or w not in Path(path).resolve().parents:
        raise RuntimeError('refusing to change %s: not inside an accept- world directly under run/' % path)


def header_entries(f):
    """Number of chunk entries (non-zero location entries) in a region file's first header sector, read-only; None without a file."""
    if not f.is_file():
        return None
    with open(f, 'rb') as fh:
        head = fh.read(4096)
    if len(head) < 4096:
        return 0
    return sum(1 for i in range(0, 4096, 4) if struct.unpack('>I', head[i:i + 4])[0] != 0)


def rows_of_region(core, rz):
    """The map rows iZ whose world z lies in region row rz (cells of column iX = 0)."""
    return [iz for iz in range(200) if cell_pos(core, 0, iz)[1] >> 9 == rz]


def extra_pillars(core, pillars):
    """The pillar for the unreadable header (middle row of the region south of the first pillars' region) and the pillar for the
    deleted file (last row of the region after that), both in column iX = 0, plus the first row of the latter region. Each region
    holds only its own pillar; the deleted region's first row lies at least 10 rows (300 blocks) north of its pillar, far outside the
    chunks saved around the pillar, so the radar reads that region's header there without loading a chunk of it."""
    rz0 = pillars[0][4] >> 9
    if any(p[4] >> 9 != rz0 for p in pillars):
        raise RuntimeError('the first pillars span two region rows: %s' % [(p[3], p[4]) for p in pillars])
    rows_h, rows_d = rows_of_region(core, rz0 + 1), rows_of_region(core, rz0 + 2)
    if not rows_h or len(rows_d) < 11:
        raise RuntimeError('no room for the extra pillars: rows %s / %s' % (rows_h, rows_d))
    ih, idl = rows_h[len(rows_h) // 2], rows_d[-1]
    hp, dp = cell_pos(core, 0, ih), cell_pos(core, 0, idl)
    return (0, ih, HEADER_TOP, hp[0], hp[1]), (0, idl, DELETED_TOP, dp[0], dp[1]), rows_d[0]


def deleted_file_probe(ctx, a, core, pillar, first_iz):
    """The chunk-file-deleted case of the module docstring, from a frozen world after the restart. Returns the readings."""
    ix, iz, ptop, px, pz = pillar
    s_first, s_pillar = index(0, first_iz) // 100, index(ix, iz) // 100
    out = dict(slice_first=s_first, slice_pillar=s_pillar)
    out['showMap_before'] = _lib.block_data(ctx, core, 'showMap')
    hud = Z.open_screen(ctx, a, (core[0], FEET, core[2] + 1), 'south', [core[0] + 0.5, FEET, core[2] + 4.5], 'MachineRadarScreen')
    left = (hud['gui_scaled_width'] - GUI_W) // 2
    top = (hud['gui_scaled_height'] - GUI_H) // 2
    if out['showMap_before'] != 1:
        ctx.step('mouse', client=a, at=[left + MAP_BUTTON[0], top + MAP_BUTTON[1]], button=0, action='click', after=2)
    # the clear flag is applied at the end of the next tick, after that tick's slice (NEO MachineRadarBlockEntity.java:185-189): set it at
    # slice s_first - 2, so slice s_first - 1 still scans the old map and slice s_first is the first one scanned on the cleared map
    _lib.align(ctx, 400, (s_first - 2) % 400, 'radar-before-clear')
    ctx.step('mouse', client=a, at=[left + CLEAR_BUTTON[0], top + CLEAR_BUTTON[1]], button=0, action='click', after=4)
    out['showMap'] = _lib.block_data(ctx, core, 'showMap')
    _lib.align(ctx, 400, s_first, 'radar-first-cell')
    out['first_cell'] = map_cell(ctx, core, index(0, first_iz))
    f = region_file(px >> 4, pz >> 4)
    disposable(f)
    out['file'] = '%s/%s' % (f.parent.name, f.name)
    out['before'] = dict(exists=f.is_file(), size=f.stat().st_size if f.is_file() else None, entries=header_entries(f))
    mark = Z.log_mark()
    if f.is_file():
        os.remove(f)
    _lib.align(ctx, 400, s_pillar, 'radar-pillar-cell')
    out['pillar_cell'] = map_cell(ctx, core, index(ix, iz))
    ctx.step('close', client=a, allow_fail=True)
    _lib.server_idle(ctx, a)
    ctx.rcon('save-all')
    time.sleep(3)
    out['after_save'] = dict(exists=f.is_file(), size=f.stat().st_size if f.is_file() else None, entries=header_entries(f))
    lines, _ = Z.log_lines(mark)
    client_lines, other = Z.bad_log_lines(lines)
    out['log_errors'] = (client_lines + other)[:5]
    return out


def saved_in_header(cx, cz):
    """Whether the chunk has a location entry in its region file's header (read here, read-only)."""
    f = world_dir() / 'region' / ('r.%d.%d.mca' % (cx >> 5, cz >> 5))
    if not f.is_file() or f.stat().st_size < 8192:
        return False
    with open(f, 'rb') as fh:
        head = fh.read(4096)
    i = ((cx & 31) + (cz & 31) * 32) * 4
    return struct.unpack('>I', head[i:i + 4])[0] != 0


def saved_stamp(cx, cz):
    """The chunk's save time (epoch seconds) from its region file's timestamp sector, None without a file or entry (read-only)."""
    f = world_dir() / 'region' / ('r.%d.%d.mca' % (cx >> 5, cz >> 5))
    if not f.is_file() or f.stat().st_size < 8192:
        return None
    with open(f, 'rb') as fh:
        head = fh.read(8192)
    i = ((cx & 31) + (cz & 31) * 32) * 4
    return struct.unpack('>I', head[4096 + i:4096 + i + 4])[0] or None


def radar_on_disk(core, cells):
    """What the region file holds for the radar's chunk (read-only): the save stamp, the number of "showMap" byte tags in the
    chunk and the first one's value, and the first "map" byte array's length and values at `cells` (raw NBT bytes of the
    zlib-compressed chunk; the radar core is the only block entity in its chunk with these names)."""
    cx, cz = core[0] >> 4, core[2] >> 4
    out = dict(stamp=saved_stamp(cx, cz))
    f = world_dir() / 'region' / ('r.%d.%d.mca' % (cx >> 5, cz >> 5))
    if not f.is_file() or f.stat().st_size < 8192:
        return out
    with open(f, 'rb') as fh:
        raw = fh.read()
    i = ((cx & 31) + (cz & 31) * 32) * 4
    sector = struct.unpack('>I', raw[i:i + 4])[0] >> 8
    if not sector:
        return out
    length, kind = struct.unpack('>IB', raw[sector * 4096:sector * 4096 + 5])
    if kind != 2:
        out['compression'] = kind
        return out
    nbt = zlib.decompress(raw[sector * 4096 + 5:sector * 4096 + 4 + length])
    tag = b'\x01\x00\x07showMap'
    out['showMap_tags'] = nbt.count(tag)
    at = nbt.find(tag)
    out['showMap'] = nbt[at + len(tag)] if at >= 0 else None
    tag = b'\x07\x00\x03map'
    at = nbt.find(tag)
    if at >= 0:
        n = struct.unpack('>i', nbt[at + len(tag):at + len(tag) + 4])[0]
        body = nbt[at + len(tag) + 4:at + len(tag) + 4 + n]
        out['map_length'] = n
        out['map_cells'] = {c: (body[c] if c < len(body) else None) for c in cells}
    return out


def map_cell(ctx, core, i):
    return _lib.block_data(ctx, core, 'map[%d]' % i)


def client_map(ctx, who, core):
    d = ctx.step('dump', client=who, **{'from': list(core)})
    nbt = _lib.parse_snbt(d['blocks'][0]['nbt']) if d['blocks'] and d['blocks'][0].get('nbt') else {}
    return nbt.get('map') or []


def run(ctx):
    a, b = list(ctx.channels)
    Z.setup_world(ctx, a, b)
    ctx.rcon('tick unfreeze')
    x, z = SITE
    # the radar opens its screen only at y >= 55 (original MachineRadarLarge.java:41-60; NEO MachineRadarLargeBlock.java:58-61): a stone
    # platform at y = PLATFORM (command site preparation), the radar placed on it by hand
    ctx.rcon('fill %d %d %d %d %d %d minecraft:stone' % (x - 6, PLATFORM, z - 8, x + 6, PLATFORM, z + 7),
             'fill %d %d %d %d %d %d minecraft:air' % (x - 6, PLATFORM + 1, z - 8, x + 6, PLATFORM + 8, z + 7))
    Z.hand(ctx, a, H + 'machine_radar_large')
    ctx.step('view', client=a, pos=[x + 0.5, FEET, z + 4.5], look_at=_lib.face_point((x, PLATFORM, z), 'up'), fly=True, hide_gui=False)
    ctx.step('use', client=a, target=dict(pos=[x, PLATFORM, z], face='up'), after=8)
    ctx.rcon('item replace entity %s hotbar.0 with minecraft:air' % a)
    d = ctx.step('dump', client=a, **{'from': [x - 4, FEET, z - 6], 'to': [x + 4, FEET + 5, z + 4]})
    cores = [tuple(int(c) for c in blk['pos']) for blk in d['blocks'] if blk['block'] == H + 'machine_radar_large' and blk['props'].get('type') == 'core']
    if len(cores) != 1:
        raise RuntimeError('large radar: expected one core, found %s' % cores)
    core = cores[0]

    # the pillars: chunks force-loaded to build them, then let go so they are saved and unloaded (command site preparation)
    pillars = []
    for ix, iz, top in PILLARS:
        px, pz = cell_pos(core, ix, iz)
        pillars.append((ix, iz, top, px, pz))
    hdr, dele, dele_first_iz = extra_pillars(core, pillars)
    built = pillars + [hdr, dele]
    for ix, iz, top, px, pz in built:
        ctx.rcon('forceload add %d %d' % (px, pz))
    for ix, iz, top, px, pz in built:
        for _ in range(60):
            if 'passed' in Z.rcon1(ctx, 'execute if loaded %d %d %d' % (px, G, pz)):
                break
            time.sleep(0.5)
        ctx.rcon('fill %d %d %d %d %d %d minecraft:stone' % (px, G, pz, px, top, pz))
    for ix, iz, top, px, pz in built:
        ctx.rcon('forceload remove %d %d' % (px, pz))
    saved = {}
    for _ in range(120):
        saved = {(px >> 4, pz >> 4): saved_in_header(px >> 4, pz >> 4) for _, _, _, px, pz in built}
        loaded = [p for _, _, _, p, q in built if 'passed' in Z.rcon1(ctx, 'execute if loaded %d %d %d' % (p, G, q))]
        if all(saved.values()) and not loaded:
            break
        time.sleep(0.5)
    else:
        raise RuntimeError('pillar chunks not saved and unloaded: saved %s, still loaded at x %s' % (saved, loaded))

    # both players near the radar (the map is synced within 50 blocks); everything near them saved before the count
    ctx.step('view', client=b, pos=[core[0] + 3.5, FEET, core[2] + 6.5], look_at=[core[0] + 0.5, FEET + 2, core[2] + 0.5], fly=True, hide_gui=False)
    _lib.server_idle(ctx, a)
    ctx.rcon('save-all')
    time.sleep(3)
    before = listing()
    stamp_before = saved_stamp(core[0] >> 4, core[2] >> 4)
    ux, uz = cell_pos(core, *UNSAVED)
    unsaved_region = 'region/r.%d.%d.mca' % (ux >> 9, uz >> 9)

    # the fourth pillar's region file made unreadable (mode 000) for the first sweep; its old mode is put back after the sweep
    hdr_file = region_file(hdr[3] >> 4, hdr[4] >> 4)
    disposable(hdr_file)
    hdr_saved = saved_in_header(hdr[3] >> 4, hdr[4] >> 4)
    hdr_mode = stat.S_IMODE(hdr_file.stat().st_mode)
    os.chmod(hdr_file, 0)
    try:
        with open(hdr_file, 'rb'):
            hdr_unreadable = False
    except PermissionError:
        hdr_unreadable = True

    # A opens the radar screen and switches the map on
    hud = Z.open_screen(ctx, a, (core[0], FEET, core[2] + 1), 'south', [core[0] + 0.5, FEET, core[2] + 4.5], 'MachineRadarScreen')
    left = (hud['gui_scaled_width'] - GUI_W) // 2
    top = (hud['gui_scaled_height'] - GUI_H) // 2
    g_click = ctx.server()['game_time']
    t_click = time.time()
    ctx.step('mouse', client=a, at=[left + MAP_BUTTON[0], top + MAP_BUTTON[1]], button=0, action='click', after=2)
    show = None
    while time.time() - t_click < 30:
        st = ctx.server()
        if st['game_time'] >= g_click + SWEEP:
            break
        if show != 1:
            show = _lib.block_data(ctx, core, 'showMap')
        time.sleep(0.5)
    wall = time.time() - t_click
    st = ctx.server()
    ticks = st['game_time'] - g_click
    lag = wall - ticks / 20.0
    tq = Z.rcon1(ctx, 'tick query')
    ctx.server('tick freeze')
    os.chmod(hdr_file, hdr_mode)
    hdr_restored = stat.S_IMODE(hdr_file.stat().st_mode) == hdr_mode
    ctx.step('close', client=a, allow_fail=True)
    ctx.step('wait', client=a, ticks=20)
    if show != 1:
        show = _lib.block_data(ctx, core, 'showMap')
    ctx.check(RD + 'mp-first-scan-lag', show == 1 and ticks >= SWEEP and lag <= 1.0,
              'map switched on %s; from game time %d (before the click) %d ticks took %.2f s wall: lag %.2f s against %d ticks at 20 '
              'per second (before the fix: about 18.5 s); tick query at the end: %s' % (show == 1, g_click, ticks, wall, lag, ticks, tq[:160]),
              ['rcon log'])

    # cells on the server
    expect = {index(ix, iz): top + 1 for ix, iz, top, _, _ in pillars}
    expect[index(*UNSAVED)] = 50
    server_cells = {i: map_cell(ctx, core, i) for i in expect}
    clients, maps = {}, {}
    for who in (a, b):
        m = maps[who] = client_map(ctx, who, core)
        clients[who] = dict(length=len(m), zeros=sum(1 for v in m if v == 0), cells={i: (m[i] if i < len(m) else None) for i in expect})
    clients_ok = all(c['length'] == 40000 and c['cells'] == server_cells for c in clients.values())
    ctx.check(RD + 'mp-first-scan-drawn', server_cells == expect and clients_ok,
              'pillar columns %s (chunks saved in the header before the scan: %s); server cells %s, expected %s; clients %s'
              % ([(px, pz, top) for _, _, top, px, pz in pillars], saved, server_cells, expect, clients), ['rcon log'])

    after = listing()
    new = sorted(set(after) - set(before))
    gone = sorted(set(before) - set(after))
    empty = sorted(k for k, v in after.items() if v == 0)
    new_region = [k for k in new if k.startswith('region/')]
    ok_files = not new_region and not gone and not [k for k in empty if k.startswith('region/')] and unsaved_region not in after
    ctx.check(RD + 'mp-first-scan-files', ok_files,
              'files before %d, after %d; new %s; gone %s; zero-byte %s; never-generated region %s present: %s'
              % (len(before), len(after), new or 'none', gone or 'none', empty or 'none', unsaved_region, unsaved_region in after),
              ['%s/region' % common.rel(world_dir())])

    # the unreadable header: the fourth pillar's cell is 50 on the server and both clients; the fifth pillar, saved the same way in a
    # readable region, is the control (drawn as its height + 1 in the same sweep)
    hi, di = index(hdr[0], hdr[1]), index(dele[0], dele[1])
    hdr_server, dele_first = map_cell(ctx, core, hi), map_cell(ctx, core, di)
    hdr_clients = {who: (maps[who][hi] if hi < len(maps[who]) else None) for who in (a, b)}
    hdr_detail = ('pillar 4 at %s (top y %d, map cell %d) in %s: saved in the header before %s, unreadable during the sweep %s (mode %o, put back %s); '
                  'cell on the server %s, clients %s (want 50); control pillar 5 at %s (top y %d) in a readable region drawn %s (want %d)'
                  % ((hdr[3], hdr[4]), hdr[2], hi, common.rel(hdr_file), hdr_saved, hdr_unreadable, hdr_mode, hdr_restored, hdr_server,
                     hdr_clients, (dele[3], dele[4]), dele[2], dele_first, dele[2] + 1))
    if not hdr_saved or not hdr_unreadable or dele_first != dele[2] + 1:
        ctx.not_run(RD + 'mp-first-scan-header-read-error', 'the case was not set up (pillar chunk saved, file unreadable, control drawn): ' + hdr_detail)
    else:
        ctx.check(RD + 'mp-first-scan-header-read-error', hdr_server == 50 and all(v == 50 for v in hdr_clients.values()), hdr_detail,
                  ['%s/region' % common.rel(world_dir())])

    # restart: the map is a stored quantity
    pre = dict(showMap=show, **{'map%d' % i: v for i, v in server_cells.items()})
    mark = Z.log_mark()
    _lib.reopen(ctx, who=a)
    _lib.server_idle(ctx, a)
    post = dict(showMap=_lib.block_data(ctx, core, 'showMap'), **{'map%d' % i: map_cell(ctx, core, i) for i in server_cells})
    cmp = _lib.compare_static(pre, post, not_quantity=('showMap',))
    rid = _lib.block_data(ctx, core, 'id')
    disk = radar_on_disk(core, list(server_cells))
    lines, _ = Z.log_lines(mark)
    stops = [ln[:10] for ln in lines if 'Stopping server' in ln]
    starts = [ln[:10] for ln in lines if 'Done (' in ln]
    clock = lambda t: time.strftime('%H:%M:%S', time.localtime(t)) if t else None
    ctx.check(RD + 'mp-first-scan-restart', cmp['ok'], 'before %s, after %s; %s; radar block entity after the restart: id %s; '
              'radar chunk %s in its region file: save stamp after the save before the scan %s, after the restart %s; server log: '
              'stopping at %s, the restarted server done at %s; on disk after the restart %s'
              % (pre, post, cmp['detail'], rid, (core[0] >> 4, core[2] >> 4), clock(stamp_before), clock(disk.get('stamp')),
                 stops, starts, {k: v for k, v in disk.items() if k != 'stamp'}), ['rcon log', 'server log'])

    # a chunk file deleted while the server runs (module docstring), after the restart in the frozen world
    f7 = deleted_file_probe(ctx, a, core, dele, dele_first_iz)
    f7_detail = ('pillar 5 at %s (top y %d) in %s; slices: region\'s first cell %d, pillar %d; showMap %s -> %s; first cell after its tick %s '
                 '(want 50: the header was read); file before the deletion %s; pillar cell after its tick %s (50 or %d); after save-all %s '
                 '(want no file or no chunk entry); server log errors since the deletion %s'
                 % ((dele[3], dele[4]), dele[2], f7['file'], f7['slice_first'], f7['slice_pillar'], f7['showMap_before'], f7['showMap'],
                    f7['first_cell'], f7['before'], f7['pillar_cell'], dele[2] + 1, f7['after_save'], f7['log_errors'] or 'none'))
    if f7['first_cell'] != 50 or not f7['before']['entries'] or f7['pillar_cell'] == 0:
        ctx.not_run(RD + 'mp-first-scan-chunk-file-deleted', 'the case was not set up (header read before the deletion, a saved chunk in the '
                    'file, the pillar cell probed): ' + f7_detail)
    else:
        ctx.check(RD + 'mp-first-scan-chunk-file-deleted', f7['pillar_cell'] in (50, dele[2] + 1) and not f7['after_save']['entries'],
                  f7_detail, ['%s/region' % common.rel(world_dir()), 'server log'])
    ctx.rcon('tick unfreeze')
