"""Goal 31 user stations for belts: what only a person watching the game can judge (animation direction, how smooth items
look through turns, lifts and chutes, the cram puff and bang). Built by stations.py; not run by drive.py.
"""
import re

SCENARIO = dict(
    id='conveyors.stations-g31',
    feature='conveyors',
    title='Goal 31 stations: belt animation, smoothness through turns, lift and chute, cram',
    group='station',
    station=True,
)

G = -60
TYPES = ('conveyor', 'conveyor_express', 'conveyor_double', 'conveyor_triple')
# a belt's facing names the side its items come from: facing=south carries them north


def cmd(ctx, command):
    ctx.step('cmd', command=command, wait_ticks=1)


def feed(ctx, x, z, item, n=64, ejector=None):
    """A chest at (x, z) and an extractor north of it that puts the chest's items on the belt north of the extractor."""
    cmd(ctx, 'setblock %d %d %d minecraft:chest[facing=north]' % (x, G, z))
    cmd(ctx, 'item replace block %d %d %d container.0 with %s %d' % (x, G, z, item, n))
    cmd(ctx, 'setblock %d %d %d hbmsntm:crane_extractor[input=north,output=south]' % (x, G, z - 1))
    if ejector:
        cmd(ctx, 'item replace block %d %d %d container.19 with hbmsntm:%s' % (x, G, z - 1, ejector))


def sink(ctx, x, z):
    """An inserter at (x, z) taking from the belt south of it into a chest north of it."""
    cmd(ctx, 'setblock %d %d %d hbmsntm:crane_inserter[input=south,output=north]' % (x, G, z))
    cmd(ctx, 'setblock %d %d %d minecraft:chest[facing=south]' % (x, G, z - 1))


def chest_items(ctx, x, z):
    r = ctx.step('cmd', command='data get block %d %d %d Items' % (x, G, z), wait_ticks=4, allow_error=True)
    return ' '.join(m.get('text', '') for m in r.get('messages', []))


# a closed 3x3 ring travelling clockwise seen from above, and its mirror travelling anticlockwise: (dx, dz, facing = the side
# the items come from, shape). Together the two rings hold straight, left and right pieces in all four facings.
CW = [(0, 0, 'south', 'right'), (1, 0, 'west', 'straight'), (2, 0, 'west', 'right'), (2, 1, 'north', 'straight'),
      (2, 2, 'north', 'right'), (1, 2, 'east', 'straight'), (0, 2, 'east', 'right'), (0, 1, 'south', 'straight')]
CCW = [(2, 0, 'south', 'left'), (1, 0, 'east', 'straight'), (0, 0, 'east', 'left'), (0, 1, 'north', 'straight'),
       (0, 2, 'north', 'left'), (1, 2, 'west', 'straight'), (2, 2, 'west', 'left'), (2, 1, 'south', 'straight')]
RING_ITEMS = 6


def _ring(ctx, t, ring, x, z):
    """the ring's top row at z; a chest two blocks north of its top middle and an extractor between them put RING_ITEMS
    iron ingots on it, few enough never to cram"""
    for dx, dz, facing, shape in ring:
        cmd(ctx, 'setblock %d %d %d hbmsntm:%s[facing=%s,shape=%s]' % (x + dx, G, z + dz, t, facing, shape))
    cmd(ctx, 'setblock %d %d %d minecraft:chest' % (x + 1, G, z - 2))
    cmd(ctx, 'item replace block %d %d %d container.0 with minecraft:iron_ingot %d' % (x + 1, G, z - 2, RING_ITEMS))
    cmd(ctx, 'setblock %d %d %d hbmsntm:crane_extractor[input=south,output=north]' % (x + 1, G, z - 1))


def _animation(ctx, x, z):
    # one row per belt type (regular, express, double, triple from the sign southwards); clockwise ring west, anticlockwise east
    for n, t in enumerate(TYPES):
        _ring(ctx, t, CW, x, z + 2 + 6 * n)
        _ring(ctx, t, CCW, x + 5, z + 2 + 6 * n)


def _animation_probe(ctx, x, z):
    ctx.step('wait', ticks=200)
    counts = []
    for n in range(4):
        for rx in (x, x + 5):
            r = ctx.step('cmd', command='execute if entity @e[type=hbmsntm:moving_item,x=%d,y=%d,z=%d,dx=2,dy=1,dz=2]' % (rx, G, z + 2 + 6 * n),
                         allow_error=True)
            text = ' '.join(m.get('text', '') for m in r.get('messages', []))
            m = re.search(r'(\d+)\s*$', text)
            counts.append(int(m.group(1)) if m else 0)
    return all(c == RING_ITEMS for c in counts), 'moving items on the eight rings after 200 ticks: %s' % counts


def _smooth(ctx, x, z):
    # chest, extractor, two belts north, a lift three high, two belts on top, a chute down onto a belt, belt, inserter, chest.
    # Two levers (placed first, on) hold the two extractors until the person flips them: an unheld feed would run out within
    # about a minute of the world opening, before anyone gets here.
    for lx in (x - 1, x + 2):
        cmd(ctx, 'setblock %d %d %d minecraft:lever[face=floor,facing=north,powered=true]' % (lx, G, z + 10))
    feed(ctx, x, z + 11, 'minecraft:iron_ingot')
    feed(ctx, x + 1, z + 11, 'minecraft:stone')
    for dz in (9, 8):
        cmd(ctx, 'setblock %d %d %d hbmsntm:conveyor[facing=south,shape=straight]' % (x, G, z + dz))
    cmd(ctx, 'setblock %d %d %d hbmsntm:conveyor[facing=east,shape=straight]' % (x + 1, G, z + 9))
    for dy in range(3):
        cmd(ctx, 'setblock %d %d %d hbmsntm:conveyor_lift[facing=south]' % (x, G + dy, z + 7))
    for dz in (6, 5):
        cmd(ctx, 'setblock %d %d %d hbmsntm:conveyor[facing=south,shape=straight]' % (x, G + 2, z + dz))
    cmd(ctx, 'setblock %d %d %d hbmsntm:conveyor[facing=south,shape=straight]' % (x, G, z + 4))
    for dy in (1, 2):
        cmd(ctx, 'setblock %d %d %d hbmsntm:conveyor_chute' % (x, G + dy, z + 4))
    for dz in (3, 2):
        cmd(ctx, 'setblock %d %d %d hbmsntm:conveyor[facing=south,shape=straight]' % (x, G, z + dz))
    sink(ctx, x, z + 1)
    # shape updates for the pieces setblock placed (a block put on top and taken away again)
    for pos in ((x, G + 3, z + 7), (x, G + 3, z + 4), (x, G + 3, z + 6), (x, G + 3, z + 5)):
        cmd(ctx, 'setblock %d %d %d minecraft:stone' % pos)
        cmd(ctx, 'setblock %d %d %d minecraft:air' % pos)


def levers_off(ctx, x, z, xs):
    for lx in xs:
        cmd(ctx, 'setblock %d %d %d minecraft:lever[face=floor,facing=north,powered=false]' % (lx, G, z))


def _smooth_probe(ctx, x, z):
    held = chest_items(ctx, x, z)
    levers_off(ctx, x, z + 10, (x - 1, x + 2))
    ctx.step('wait', ticks=400)
    if 'iron_ingot' in held or 'stone' in held:
        return False, 'the sink chest had items before the levers were flipped: %s' % held[:200]
    text = chest_items(ctx, x, z)
    return 'iron_ingot' in text and 'stone' in text, 'sink chest after 400 ticks: %s' % text[:200]


# the cram ring: a closed 3x3 clockwise ring of regular belts (CW above) at z + 2 .. z + 4
CRAM_FEEDS = (0, 2)  # extractors north of the ring's two top corners, chests north of them, the lever between the extractors


def _cram(ctx, x, z):
    # Two extractors with the Mk.III ejection upgrade put cobblestone on a closed ring every 2 ticks each: the ring never lets
    # them go, so after a few laps 25 or more sit within one item's reach and the next check pops them (default limit 25,
    # MovingConveyorObject.cramCheck; original EntityMovingConveyorObject.java:85-100). Only items with an even entity id
    # check (the original's ticksExisted + id): in single player the client's copy of every item takes the next id from the
    # same counter, so items fed one at a time all share one parity; the two extractors act in the same tick (world time
    # modulo the delay), their items get consecutive ids and both parities are on the ring. The lever (placed first, on)
    # holds both extractors until the person flips it.
    cmd(ctx, 'setblock %d %d %d minecraft:lever[face=floor,facing=north,powered=true]' % (x + 1, G, z + 1))
    for dx in CRAM_FEEDS:
        cmd(ctx, 'setblock %d %d %d minecraft:chest' % (x + dx, G, z))
        cmd(ctx, 'data merge block %d %d %d {Items:[%s]}' % (x + dx, G, z, ','.join(
            '{Slot:%db,id:"minecraft:cobblestone",count:64}' % k for k in range(3))))
        cmd(ctx, 'setblock %d %d %d hbmsntm:crane_extractor[input=south,output=north]' % (x + dx, G, z + 1))
        cmd(ctx, 'item replace block %d %d %d container.19 with hbmsntm:upgrade_ejector_3' % (x + dx, G, z + 1))
    for dx, dz, facing, shape in CW:
        cmd(ctx, 'setblock %d %d %d hbmsntm:conveyor[facing=%s,shape=%s]' % (x + dx, G, z + 2 + dz, facing, shape))


def count_entities(ctx, kind, box):
    r = ctx.step('cmd', command='execute if entity @e[type=%s,%s]' % (kind, box), allow_error=True)
    text = ' '.join(m.get('text', '') for m in r.get('messages', []))
    if r.get('status') != 'ok':
        return None, text
    m = re.search(r'(\d+)\s*$', text.strip())
    return (int(m.group(1)) if m and ('passed' in text or '通过' in text) else 0), text


def _cram_probe(ctx, x, z):
    """flips the lever and watches the ring: an explosion shows as moving items gone at once or a ring belt destroyed"""
    box = 'x=%d,y=%d,z=%d,dx=2,dy=1,dz=2' % (x, G, z + 2)
    held, text = count_entities(ctx, 'hbmsntm:moving_item', box)
    if held is None or held:
        return False, 'before the lever: moving items on the ring %s (%s)' % (held, text[:120])
    cmd(ctx, 'setblock %d %d %d minecraft:lever[face=floor,facing=north,powered=false]' % (x + 1, G, z + 1))
    seen, peak = [], 0
    for step in range(60):
        ctx.step('wait', ticks=20)
        n, text = count_entities(ctx, 'hbmsntm:moving_item', box)
        if n is None:
            return False, 'count failed after %d ticks: %s' % (20 * (step + 1), text[:120])
        belts = len([b for b in ctx.step('dump', **{'from': [x, G, z + 2], 'to': [x + 2, G, z + 4]})['blocks'] if b['block'] == 'hbmsntm:conveyor'])
        seen.append((20 * (step + 1), n, belts))
        peak = max(peak, n)
        if belts < 8 or n < peak - 10:
            return True, 'popped after %d ticks: moving items peaked at %d, now %d; ring belts left %d of 8; samples %s' % (
                20 * (step + 1), peak, n, belts, seen[-6:])
    return False, 'no pop in 1200 ticks: samples (ticks, moving items, ring belts) %s' % seen[-8:]


VEC = dict(north=(0, -1), south=(0, 1), east=(1, 0), west=(-1, 0))
OPP = dict(north='south', south='north', east='west', west='east')
CCW_OF = dict(north='west', west='south', south='east', east='north')


def _splitter_cores(x, z):
    """(core cell, facing) of the four splitters, facing = the side items come from: north and south side by side in two
    columns (second blocks west and east of the cores), east and west in two rows south of them (second blocks north and
    south); each runs seven cells along its travel direction"""
    return [((x + 2, z + 4), 'north'), ((x + 5, z + 4), 'south'), ((x + 4, z + 11), 'east'), ((x + 4, z + 14), 'west')]


def _splitter(ctx, x, z):
    # each splitter is placed by hand (a two-block structure): the player looks along the travel direction onto the core cell;
    # a chest and an extractor feed the core lane from the facing side; each lane runs one belt into an inserter and a chest
    cmd(ctx, 'item replace entity @s weapon.mainhand with hbmsntm:crane_splitter 4')
    for (cx, cz), f in _splitter_cores(x, z):
        d = OPP[f]
        vx, vz = VEC[d]
        ctx.step('view', pos=[cx + 0.5 - 2 * vx, G, cz + 0.5 - 2 * vz], look_at=[cx + 0.5, G - 0.5, cz + 0.5], fly=False, hide_gui=True)
        ctx.step('use', target=dict(pos=[cx, G - 1, cz], face='up'), after=6)
    cmd(ctx, 'item replace entity @s weapon.mainhand with minecraft:air')
    for (cx, cz), f in _splitter_cores(x, z):
        fx, fz = VEC[f]
        ox, oz = VEC[OPP[f]]
        sx, sz = VEC[CCW_OF[f]]
        cmd(ctx, 'setblock %d %d %d hbmsntm:conveyor[facing=%s,shape=straight]' % (cx + fx, G, cz + fz, f))
        cmd(ctx, 'setblock %d %d %d hbmsntm:crane_extractor[input=%s,output=%s]' % (cx + 2 * fx, G, cz + 2 * fz, OPP[f], f))
        cmd(ctx, 'setblock %d %d %d minecraft:chest' % (cx + 3 * fx, G, cz + 3 * fz))
        cmd(ctx, 'data merge block %d %d %d {Items:[%s]}' % (cx + 3 * fx, G, cz + 3 * fz, ','.join(
            '{Slot:%db,id:"minecraft:iron_ingot",count:64}' % k for k in range(27))))
        for lx, lz in ((cx, cz), (cx + sx, cz + sz)):
            cmd(ctx, 'setblock %d %d %d hbmsntm:conveyor[facing=%s,shape=straight]' % (lx + ox, G, lz + oz, f))
            cmd(ctx, 'setblock %d %d %d hbmsntm:crane_inserter[input=%s,output=%s]' % (lx + 2 * ox, G, lz + 2 * oz, f, OPP[f]))
            cmd(ctx, 'setblock %d %d %d minecraft:chest' % (lx + 3 * ox, G, lz + 3 * oz))


def _splitter_probe(ctx, x, z):
    # what the feed chests still hold right after the saved world opens: one extractor sends one ingot a second
    left = []
    for (cx, cz), f in _splitter_cores(x, z):
        fx, fz = VEC[f]
        left.append(sum(int(v) for v in re.findall(r'count:\s*(\d+)', chest_items(ctx, cx + 3 * fx, cz + 3 * fz))))
    ctx.step('wait', ticks=240)
    got = []
    for (cx, cz), f in _splitter_cores(x, z):
        ox, oz = VEC[OPP[f]]
        sx, sz = VEC[CCW_OF[f]]
        lanes = []
        for lx, lz in ((cx, cz), (cx + sx, cz + sz)):
            m = re.findall(r'count:\s*(\d+)', chest_items(ctx, lx + 3 * ox, lz + 3 * oz))
            lanes.append(sum(int(v) for v in m))
        got.append((f, lanes))
    return all(a > 0 and b > 0 for _, (a, b) in got) and min(left) >= 20 * 60, (
        'iron in the two lane chests per splitter facing after 240 ticks: %s; feed chests when this probe started %s (one a second, so '
        'at least %.0f minutes of feed)' % (got, left, min(left) / 60.0))


STATIONS = [
    dict(id='conveyors.station-animation', short=['BELT ARROWS', 'rings: CW west', 'CCW east'],
         todo='八个小环，从牌子往南一排一种皮带：普通、快速、双轨、三轨；每排西边的环顺时针转、东边的环逆时针转（从上往下看），每个环上有 6 个铁锭一直转圈。飞到环的上方往下看，逐格看皮带顶面的条纹或箭头往哪边动：直的四个方向、左弯、右弯都在环里。',
         expect='每一格（直、左弯、右弯，四个朝向）顶面的花纹都朝那一格上物品前进的方向移动，弯道的花纹跟着拐弯；快速皮带的花纹和物品都明显更快。哪一格走反或侧着走，记下第几排、哪个环、哪一格。',
         build=_animation, probe=_animation_probe, size=(8, 2, 24)),
    dict(id='conveyors.station-smooth', short=['SMOOTH', 'lift up and', 'chute down'],
         todo='先扳下两个箱子两侧的两个拉杆（关掉红石，两台提取器开始送料；不扳时什么也不动）。看铁锭和石头从箱子出来，沿皮带往北、拐进垂直输送带升上去、在上面走两格、从滑槽落回地面、进末端的箱子。走近看，再退到约 10 格外看。料约一分钟送完，要再看就按复位按钮再扳拉杆。',
         expect='物品平放（方块直立），一路连贯移动，不跳、不抖、不闪；上升和下落都连贯，没有卡住；相邻两个物品不会闪烁。',
         build=_smooth, probe=_smooth_probe, size=(3, 4, 12)),
    dict(id='conveyors.station-cram', short=['CRAM', 'flip lever', 'stand back'],
         todo='站开 3 格以上，扳一下两台提取器中间的拉杆（关掉红石，两台提取器开始往一个封闭的小环上快速送圆石）。环上的物品越积越密，十来秒后在某一处挤满。约 1 分钟还没有爆开，就退出世界再进来接着等。看完按复位按钮（地上散落的圆石要自己清掉或不管）。',
         expect='某一处挤满后一声小爆炸，冒出一团黄色烟和灰色烟，那一堆物品消失；默认设置下，做检查的物品在环上待了 10 秒以上时，它脚下那格皮带也被炸掉（原版同样），环从那里断开，后面的物品从缺口掉到地上。不伤人，旁边的方块不坏。（只有编号为偶数的物品做拥堵检查，原版也这样；单人世界里一台提取器送出的物品编号往往同为奇数，两台在同一刻送料就两种都有，所以这里用两台。）',
         build=_cram, probe=_cram_probe, size=(3, 2, 5)),
    dict(id='conveyors.station-splitter', short=['SPLITTER', '4 facings', 'see sheet'],
         todo='方向：走廊沿东西向，往东走站点编号增大，站点都在牌子南侧（按 F3 看“Facing”也行）。四台分离器：北边两列，西列朝北、东列朝南；南边两行，北行朝东、南行朝西（“朝”指物品来的一侧；各由放置者顺着物品前进方向看着放下），每台由一个箱子和提取器从进料一侧送铁锭，两条出料道各进一个箱子。没有铁锭在动就先按复位按钮。逐台从上方和侧面看：两格的外壁、中间的皮带面、左右两半的贴图；再打开创造物品栏搜“分离器”与“分隔器”（英文 Splitter、Partitioner），看两个物品图标。',
         expect='四台的外形都与放置方向对得上：两侧外壁沿着物品前进方向，左右两半贴图不同；中间的皮带面花纹朝物品前进的方向动，与物品一致；物品分到两条道。分离器与分隔器的物品图标都在格子里居中、不出格。哪台不对，记下朝向。',
         build=_splitter, probe=_splitter_probe, size=(8, 2, 16)),
]


def expectations():
    return [dict(id=s['id'], text=s['expect'], source='user station') for s in STATIONS]
