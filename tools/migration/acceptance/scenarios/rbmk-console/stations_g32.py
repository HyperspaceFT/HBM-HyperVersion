"""Goal 32 user station for the RBMK console: the AZ-5 lid and shutdown sounds heard by the operator, and the console screen and
model as a person sees them. Built by stations.py; not run by drive.py.

Rig: a row of a manual control rod, a blank column and a second control rod, an RBMK console 6 blocks south of the blank column,
linked to it with the console linking device (plain right-click on the column, sneaking right-click on the console).

Expected (original 1.7.10 / NEO):
- the console's AZ-5 button is behind a lid: the first click lifts the lid (a cover sound), the second presses the button, plays the
  shutdown sound on the clicking client only and sends level 0 to every manual control rod of the grid (original
  GUIRBMKConsole.java:222-239; NEO RBMKConsoleScreen.java:275-291, RBMKConsoleBlockEntity.java:377-392);
- the console's screens show the linked columns (grid, tooltips) and switch type with the screen-type buttons, the console model's
  screens following (original GUIRBMKConsole, RenderRBMKConsole; NEO RBMKConsoleScreen.java, RBMKConsoleBlockEntity.java:309-320).
The sound, the icons and the model are the person's to judge; that only the operator hears the alarm needs two players.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _stations_g32 as S  # noqa: E402

SCENARIO = dict(
    id='rbmk-console.stations-g32',
    feature='rbmk-console',
    title='Goal 32 station: RBMK console AZ-5 sounds and the console screen and model',
    group='station',
    station=True,
)

G, H = S.G, S.H


def _console(ctx, x, z):
    cells, core, facing = S.build_rbmk_row(ctx, x + 3, z, ['rbmk_control', 'rbmk_blank', 'rbmk_control'], 'rbmk_console')
    S.link_console(ctx, cells[1], core, facing)


def _console_probe(ctx, x, z):
    """the console is still linked to the blank column after the reload, and a plain right-click opens its screen"""
    core, facing = S.find_core(ctx, H + 'rbmk_console', (x - 1, G, z + 2), (x + 9, G + 4, z + 12))
    text = S.block_data_text(ctx, core)
    linked = (S.number_after(text, 'tX'), S.number_after(text, 'tZ')) == (x + 4, z)
    v = S.facing_vec(facing)
    S.use_face(ctx, core, facing, [core[0] + 0.5 + v[0] * 2.5, G, core[2] + 0.5 + v[1] * 2.5], offset=[0.0, 0.5, 0.0], fly=True, after=8)
    r = ctx.step('screen', expect='RBMKConsoleScreen', allow_fail=True)
    ctx.step('close', allow_fail=True)
    return linked and r.get('status') == 'ok', 'console target (tX, tZ) %s, want %s; screen after a plain right-click: %s' % (
        (S.number_after(text, 'tX'), S.number_after(text, 'tZ')), (x + 4, z), r.get('screen'))


STATIONS = [
    dict(id='rbmk-console.station-az5-console', short=['RBMK CONSOLE', 'lid, AZ-5', 'listen'],
         stands_for=['rbmk-console.mp-console-az5', 'rbmk-console.mp-console-visual'],
         todo='站在控制台前右键打开界面。先看网格里的两根控制棒；点屏幕类型键（左上的小按钮）切换几次，看图标和面前控制台模型上的屏幕有没有跟着变。然后在界面左下找 AZ-5：第一下点盖子（掀开），第二下点红色按钮。听两下的声音。再点屏幕类型键，看网格。要重做先按复位按钮。',
         expect='界面里网格画出三根柱子（两根控制棒、中间一根空白柱），悬停有提示；屏幕类型键点一下图标与网格换样子，控制台模型上的屏幕随之改画，没有错位或闪烁；点盖子响一声轻的“咔”，点 AZ-5 响一声明显的关机警报声，只在点按钮的你这里响（这一格里只有你一个人；“旁人听不到”要两名玩家，不在本站）；界面没有英文键名或乱码。',
         build=_console, probe=_console_probe, size=(9, 4, 12)),
]


def expectations():
    return S.station_expectations(STATIONS)
