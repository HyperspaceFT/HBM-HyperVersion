"""Goal 32 user station for four concrete blocks: names and looks. Built by stations.py; not run by drive.py.

Expected (original 1.7.10 / NEO): the four blocks of the ducrete family carry the original's English names and textures: the plain
one "Ducrete Tile", the smooth one "Ducrete", "Reinforced Ducrete" and the brick one "Ducrete Bricks" (original en_US.lang:5284,5560,
5562,6359; blocks ModBlocks.java:324-325,332,284; NEO NtmBlocks.java:272-275). Name and texture are the person's to judge; the blocks
are placed to be looked at, struck with a pickaxe and picked up.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _stations_g32 as S  # noqa: E402

SCENARIO = dict(
    id='concrete.stations-g32',
    feature='concrete',
    title='Goal 32 station: ducrete block names and textures',
    group='station',
    station=True,
)

G = S.G
BLOCKS = ('ducrete', 'ducrete_smooth', 'reinforced_ducrete', 'brick_ducrete')


def _blocks(ctx, x, z):
    for i, name in enumerate(BLOCKS):
        S.cmd(ctx, 'setblock %d %d %d hbmsntm:%s' % (x + 2 * i, G, z + 1, name))
    S.chest(ctx, x + 3, z + 4, [(i, 'hbmsntm:' + name, 1) for i, name in enumerate(BLOCKS)], facing='north')


def _blocks_probe(ctx, x, z):
    d = ctx.step('dump', **{'from': [x, G, z + 1], 'to': [x + 6, G, z + 1]})
    seen = sorted(b['block'] for b in d['blocks'])
    want = sorted('hbmsntm:' + n for n in BLOCKS)
    return seen == want, 'blocks in the row %s' % seen


STATIONS = [
    dict(id='concrete.station-ducrete-look', short=['DUCRETE', 'names and', 'textures'],
         stands_for=[],
         todo='看一排四块方块的外观；对每一块按住鼠标中键（或拿着它）看名字：从箱子里拿出四种放进物品栏，悬停看名字，再放在地上，用镐挖下来看掉落。在 JEI 里搜 ducrete，比一比名字和贴图。',
         expect='四块的名字对得上原版（英文：Ducrete Tile、Ducrete、Reinforced Ducrete、Ducrete Bricks；中文照中文语言包，都不是翻译键或乱码；哪一块的英文名与这四个不同就记下来）；贴图各不相同、没有紫黑方块或错位；镐挖下掉落各自本身。',
         build=_blocks, probe=_blocks_probe, size=(7, 1, 5)),
]


def expectations():
    return S.station_expectations(STATIONS)
