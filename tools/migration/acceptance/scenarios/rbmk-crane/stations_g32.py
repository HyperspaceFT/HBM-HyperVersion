"""Goal 32 user station for the RBMK crane: the console's indicator lights and the crane and hook drawn over the reactor, as the
person at the keys sees them. Built by stations.py; not run by drive.py.

Rig: three fuel channels in a row, a natural uranium rod in the western one, a crane console 6 blocks south of the middle channel,
linked to it with the console linking device (sneaking right-click on the middle column from the western column's top, then a
sneaking right-click on the console's front).

Expected (original 1.7.10 TileEntityCraneConsole / NEO RBMKCraneConsoleBlockEntity):
- the crane is centred over the linked column; the first player found in the box in front of the console (three blocks wide, two
  high, two towards the facing) steers it while a direction key is held, 0.05 a tick, and the load key lowers the hook 0.04 a tick,
  takes a rod out of a loadable column or puts the held one in, and lifts again (original TileEntityCraneConsole.java:98-176,
  NEO RBMKCraneConsoleBlockEntity.java:104-178);
- the position and lift reach the client with the block entity's packets, and the crane, the hook and the console's indicator lights
  are drawn from them (original TileEntityCraneConsole.java:96, RenderCraneConsole; NEO RBMKCraneConsoleBlockEntity.java:106,306-350).
Whether the lights and the animation look right is the person's call; the two-players half needs two players.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _stations_g32 as S  # noqa: E402

SCENARIO = dict(
    id='rbmk-crane.stations-g32',
    feature='rbmk-crane',
    title='Goal 32 station: RBMK crane lights, crane and hook as a person sees them',
    group='station',
    station=True,
)

G, H = S.G, S.H
ROD = H + 'rbmk_fuel_ueu'


def _crane(ctx, x, z):
    cells, core, facing = S.build_rbmk_row(ctx, x + 3, z, ['rbmk_rod', 'rbmk_rod', 'rbmk_rod'], 'rbmk_crane_console')
    S.merge(ctx, cells[0], S.items_snbt([(0, ROD, 1)]))
    S.link_console(ctx, cells[1], core, facing, from_top_of=cells[0])


def _crane_probe(ctx, x, z):
    """after the reload the console is still centred over the middle channel and the western channel still holds its rod"""
    core, facing = S.find_core(ctx, H + 'rbmk_crane_console', (x - 1, G, z + 2), (x + 9, G + 4, z + 12))
    text = S.block_data_text(ctx, core)
    centre = (S.number_after(text, 'centerX'), S.number_after(text, 'centerZ'))
    rod = ROD in S.block_data_text(ctx, (x + 3, G, z))
    return centre == (x + 4, z) and rod, 'crane centre (x, z) %s, want %s; western channel holds the rod %s' % (centre, (x + 4, z), rod)


STATIONS = [
    dict(id='rbmk-crane.station-crane', short=['RBMK CRANE', 'stand at keys', 'watch the hook'],
         stands_for=['rbmk-crane.mp-crane-visual'],
         todo='站到吊车控制台正前方约 1.5 格处（面对着控制台，在它前面的检测范围内）。按住左右（或上下，看控制台朝向）方向键，让吊车在三根燃料通道上方移动，再按回车（装卸键）：吊钩下降，西边通道里的燃料棒被取出，再移到东边的通道放进去。边做边抬头看反应堆上方的吊车和吊钩，低头看控制台上的指示灯。',
         expect='控制台上的指示灯随吊车位置亮在对应的位置，吊车随按键平滑移动、停在通道正上方；装卸键按下后吊钩平滑降到通道里，取出或放入燃料棒，再升回；指示灯与吊车位置一致、没有闪烁或跳变；画面里没有东西穿模或消失。（两个人同时在检测范围内时谁控制吊车要两名玩家，不在本站。）',
         build=_crane, probe=_crane_probe, size=(9, 5, 12)),
]


def expectations():
    return S.station_expectations(STATIONS)
