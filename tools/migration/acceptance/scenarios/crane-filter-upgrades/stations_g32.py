"""Goal 32 user station for the filter tag modes: what the sorter's and the extractor's filter screens write when a steel ingot, an
iron powder or a copper ingot goes into a filter slot. Built by stations.py; not run by drive.py.

Expected (original 1.7.10 / NEO): a filter slot set to an item picks the item's ore-dictionary-style mode in the smart order ingot,
block, dust, nugget, plate (original ModulePatternMatcher.java:30-53); NEO's names for them are the published c: tags, iron powder
c:dusts/iron, the steel ingot c:ingots/steel, HBM's copper ingot c:ingots/copper (NEO ModulePatternMatcher smart init,
NtmItemTagProvider.java), and cycling the mode steps through the parent tags too (c:dusts, c:ingots). The mode text on the screen,
and how the cycling feels, are the person's to judge.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _stations_g32 as S  # noqa: E402

SCENARIO = dict(
    id='crane-filter-upgrades.stations-g32',
    feature='crane-filter-upgrades',
    title='Goal 32 station: filter tag mode text for iron powder, steel ingot and copper ingot',
    group='station',
    station=True,
)

G, H = S.G, S.H


def _filters(ctx, x, z):
    S.cmd(ctx, 'setblock %d %d %d hbmsntm:crane_router' % (x + 1, G, z + 1))
    S.cmd(ctx, 'setblock %d %d %d hbmsntm:crane_extractor[input=north,output=south]' % (x + 5, G, z + 1))
    S.chest(ctx, x + 3, z + 4, [(0, H + 'powder_iron', 1), (1, H + 'ingot_steel', 1), (2, H + 'ingot_copper', 1), (3, 'minecraft:iron_ingot', 1)],
            facing='north')


def _filters_probe(ctx, x, z):
    S.use_face(ctx, (x + 1, G, z + 1), 'south', [x + 1.5, G, z + 3.5], offset=[0.0, -0.1, -0.45], after=8)
    r = ctx.step('screen', expect='Router', allow_fail=True)
    ctx.step('close', allow_fail=True)
    return r.get('status') == 'ok', 'screen after a plain right-click on the sorter: %s' % r.get('screen')


STATIONS = [
    dict(id='crane-filter-upgrades.station-tag-filter', short=['FILTER TAGS', 'iron dust/steel', 'copper ingot'],
         stands_for=[],
         todo='箱子里有铁粉、钢锭、HBM 铜锭和一个普通铁锭。右键打开分拣机，把铁粉放进一个空的过滤格（鼠标拿起铁粉，点那一格），悬停读模式文字；再放钢锭、铜锭各一格，各悬停读一次；再把普通铁锭放一格对比。然后点已放入物品的过滤格循环模式（左键、右键各试几次），看会经过哪几档。提取器（右边）同样做一遍。',
         expect='放进空格后，模式文字自动选了对应的标签：铁粉是 c:dusts/iron，钢锭是 c:ingots/steel，铜锭是 c:ingots/copper（不是“物品与元数据相同”）；循环模式时依次经过更宽的父标签（例如 c:ingots、c:dusts）而不乱跳；提取器与分拣机显示一致；文字没有被截断出格或显示成翻译键。',
         build=_filters, probe=_filters_probe, size=(7, 1, 5)),
]


def expectations():
    return S.station_expectations(STATIONS)
