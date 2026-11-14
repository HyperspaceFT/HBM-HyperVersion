"""Goal 31 user stations for crane screens: the JEI drag highlight over filter slots and the physical Shift key on a
crane tooltip. Built by stations.py; not run by drive.py.
"""
SCENARIO = dict(
    id='crane-filter-upgrades.stations-g31',
    feature='crane-filter-upgrades',
    title='Goal 31 stations: JEI drag highlight on filter slots, physical Shift on a crane tooltip',
    group='station',
    station=True,
)

G = -60


def _jei(ctx, x, z):
    ctx.step('cmd', command='setblock %d %d %d hbmsntm:crane_extractor[input=north,output=south]' % (x, G, z), wait_ticks=1)
    ctx.step('cmd', command='setblock %d %d %d hbmsntm:crane_router' % (x + 2, G, z), wait_ticks=1)


def _shift(ctx, x, z):
    ctx.step('cmd', command='setblock %d %d %d minecraft:chest[facing=south]' % (x, G, z), wait_ticks=1)
    for slot, item in enumerate(('hbmsntm:crane_router', 'hbmsntm:crane_extractor', 'hbmsntm:crane_splitter')):
        ctx.step('cmd', command='item replace block %d %d %d container.%d with %s 1' % (x, G, z, slot, item), wait_ticks=1)


STATIONS = [
    dict(id='crane-filter-upgrades.station-jei-highlight', short=['JEI DRAG', 'drag iron', 'onto filter'],
         todo='右键打开提取器，在右侧 JEI 列表里搜 iron，按住铁锭拖到界面上方一个空的过滤格上松开（每台只拖一次，拖到空格子上），松开后把鼠标停在那一格上看提示；再拖一次到缓冲格或物品栏上。然后打开旁边的分拣机，同样拖一次到空的过滤格并悬停。若要重做先按复位按钮：拖到已经有物品的格子会把模式往下切一档。',
         expect='拖动时过滤格高亮；松开后那一格出现铁锭，悬停时提示里的模式是“物品与元数据相同”（提取器与分拣机都是）；拖到缓冲或物品栏上什么也不生成。',
         build=_jei, size=(3, 1, 1)),
    dict(id='crane-filter-upgrades.station-shift', short=['SHIFT KEY', 'hold Shift', 'over items'],
         todo='打开箱子，鼠标指着分拣机、提取器、分离器，按住真实的 Shift 键再松开；按住 Shift 时切到别的程序（Cmd-Tab），在那边松开 Shift 再切回；切回后若出现暂停菜单，先点“回到游戏”，再打开箱子指一次。',
         expect='按住 Shift 时“按住 Shift 显示更多”的提示换成说明行，松开恢复；切回后 Shift 不会卡住（提示正常）。',
         build=_shift, size=(1, 1, 1)),
]


def expectations():
    return [dict(id=s['id'], text=s['expect'], source='user station') for s in STATIONS]
