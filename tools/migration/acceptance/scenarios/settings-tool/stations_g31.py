"""Goal 31 user stations for the two settings tool keys on a Mac: a trackpad Ctrl-click on a duct and a held Alt across a
Cmd-Tab. Both were judged on Windows only; macOS turns Ctrl-click into a right click at the system level, which only a
person at a Mac can see. Built by stations.py; not run by drive.py.

Expected values follow the 1.7.10 original at cd0cff450: with the paste-to-connected key held, a fluid identifier changes
the whole run of connected ducts of the same type (FluidDuctBase.java:82-101, changeTypeRecursively at :100); the held switch key steps the settings
tool's highlighted entry about every 0.25 s and stops when the key is let go.
"""
SCENARIO = dict(
    id='settings-tool.stations-g31',
    feature='settings-tool',
    title='Goal 31 stations (Mac only): Ctrl-click on a duct, held Alt across Cmd-Tab',
    group='station',
    station=True,
)

G = -60
# fluid type ids are saved numbers that never shift: NONE 0, WATER 1 (Fluids.java, the order of the constructors)
WATER_IDENTIFIER = 'hbmsntm:fluid_identifier_multi[minecraft:custom_data={Fluid1:1,Fluid2:0}]'


def cmd(ctx, command):
    ctx.step('cmd', command=command, wait_ticks=1)


def _ducts(ctx, x, z):
    # ten ducts along x with a gap after the fourth: two runs, 4 and 5 long
    for dx in range(10):
        if dx != 4:
            cmd(ctx, 'setblock %d %d %d hbmsntm:fluid_duct_neo' % (x + dx, G, z + 2))
    cmd(ctx, 'setblock %d %d %d minecraft:chest[facing=south]' % (x, G, z))
    cmd(ctx, 'item replace block %d %d %d container.0 with %s 1' % (x, G, z, WATER_IDENTIFIER))


def _alt(ctx, x, z):
    cmd(ctx, 'setblock %d %d %d hbmsntm:crane_router' % (x + 2, G, z + 2))
    cmd(ctx, 'item replace block %d %d %d container.0 with minecraft:iron_ingot 1' % (x + 2, G, z + 2))
    cmd(ctx, 'item replace block %d %d %d container.5 with minecraft:gold_ingot 1' % (x + 2, G, z + 2))
    cmd(ctx, 'setblock %d %d %d minecraft:chest[facing=south]' % (x, G, z))
    cmd(ctx, 'item replace block %d %d %d container.0 with hbmsntm:settings_tool 1' % (x, G, z))


STATIONS = [
    dict(id='settings-tool.station-mac-ctrl-click', short=['MAC ONLY', 'Ctrl-click', 'a duct'],
         todo='只在 Mac 上做（Windows 上已经判过）。从箱子拿出主类型是“水”的多类型流体识别码，拿在主手（图标颜色不代表类型，悬停看提示文字确认主类型是水），用触控板按住左 Ctrl 单击（或鼠标按住左 Ctrl 右键）靠箱子一侧那段管道（4 格）中的一格。',
         expect='靠箱子一侧相连的 4 格管道一起变成水，断开后的另一段 5 格不变；系统没有弹出右键菜单，游戏收到的是“按住 Ctrl 的右键”。',
         build=_ducts, size=(10, 1, 3)),
    dict(id='settings-tool.station-mac-alt-switch', short=['MAC ONLY', 'hold Alt', 'Cmd-Tab'],
         todo='只在 Mac 上做。从箱子拿出设定工具，拿在主手，按住 Shift 右键分拣机复制；然后按住左 Option（Alt）几秒，看屏幕左侧的提示；按住 Option 时 Cmd-Tab 切到别的程序，在那边松开 Option，再切回来。切回后多半会看到暂停菜单（游戏失去焦点时自动暂停，暂停时高亮本来就不动），先点“回到游戏”，再看几秒高亮还换不换。',
         expect='按住 Option 时提示里的高亮项约每 0.25 秒换一个；关掉暂停菜单回到游戏后，高亮停在某一项不再切换（Option 没有卡住）。',
         build=_alt, size=(3, 1, 3)),
]


def expectations():
    return [dict(id=s['id'], text=s['expect'], source='user station') for s in STATIONS]
