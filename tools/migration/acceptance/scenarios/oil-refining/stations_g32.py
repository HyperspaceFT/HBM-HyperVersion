"""Goal 32 user station for the oil refinery's drawing: the tower stays drawn when the core block is out of the view. Built by
stations.py; not run by drive.py.

Expected (original 1.7.10 / NEO): the refinery's tower is drawn whenever the core is within render distance, whatever part of the machine is in
the frustum: the original gives the tile entity an infinite render box and a render distance of 256 blocks (original
TileEntityMachineRefinery.java:341-350); NEO's renderer returns an infinite box and draws off screen (NEO RenderRefinery.java:41-44).
Only a person walking around it sees whether the tower pops in or out.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _stations_g32 as S  # noqa: E402

SCENARIO = dict(
    id='oil-refining.stations-g32',
    feature='oil-refining',
    title='Goal 32 station: the refinery tower stays drawn from the side and from below',
    group='station',
    station=True,
)

G, H = S.G, S.H


def _refinery(ctx, x, z):
    S.place_machine(ctx, 'machine_refinery', x + 5, z + 3, radius=4, height=12)


def _refinery_probe(ctx, x, z):
    core, facing = S.find_core(ctx, H + 'machine_refinery', (x, G, z - 1), (x + 10, G + 12, z + 8))
    return True, 'refinery core %s facing %s' % (core, facing)


STATIONS = [
    dict(id='oil-refining.station-refinery-look', short=['REFINERY', 'walk around', 'look up'],
         stands_for=[],
         todo='围着炼油厂走一圈：贴着底座的一侧站（让底座的核心块离出视野），抬头看塔顶；再转身背对它、再转回来；从很近的侧面慢慢转动视角；最后退到 30 格外再看一眼。反复几次，盯着塔身有没有一闪一灭。',
         expect='不论站在哪一侧、视角怎么转，塔身始终完整画着，不会在核心块移出视野的那一刻整座塔消失、也不会一闪一灭；远处（256 格内）也一直画着。',
         build=_refinery, probe=_refinery_probe, size=(10, 12, 8)),
]


def expectations():
    return S.station_expectations(STATIONS)
