"""Goal 32 user station for the power switch: its click sound, heard in single player. Built by stations.py; not run by drive.py.

Expected (original 1.7.10 / NEO): a power switch plays the reactor-start sound at the block's corner, pitch 1.0 when it is switched
on and 0.85 when it is switched off, and only on a right-click without sneaking (original CableSwitch.java:52,55; NEO
CableSwitchBlock.java:55-64). Whether the sound is right, in the right place and at the right volume is the person's call. The
dedicated-server half (both players hear it) is not a single-player station.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _stations_g32 as S  # noqa: E402

SCENARIO = dict(
    id='power-control.stations-g32',
    feature='power-control',
    title='Goal 32 station: the power switch click sound, on and off, left and right',
    group='station',
    station=True,
)

G = S.G


def _switches(ctx, x, z):
    # two switches eight blocks apart: standing between them, the left one sounds from the left and the right one from the right
    for dx in (0, 8):
        S.cmd(ctx, 'setblock %d %d %d hbmsntm:cable_switch' % (x + dx, G, z + 1))


def _switches_probe(ctx, x, z):
    """clicks the left switch on and off like a player and records the sounds the client engine was handed"""
    pos = (x, G, z + 1)
    ctx.step('sounds', action='start')
    hits = []
    for _ in range(2):
        hits.append((S.use_face(ctx, pos, 'south', [x + 0.5, G, z + 4.0], after=12).get('hit') or {}).get('pos'))
    ctx.step('wait', ticks=10)
    plugs = S.sounds_of(ctx.step('sounds', action='stop'), 'reactor_start')
    pitches = [round(p['pitch'], 2) for p in plugs]
    ok = pitches == [1.0, 0.85] and all(h == list(pos) for h in hits)
    return ok, 'two clicks hit %s; reactor_start sounds (pitches in order) %s, want [1.0, 0.85]' % (hits, pitches)


STATIONS = [
    dict(id='power-control.station-switch-sound', short=['SWITCH SOUND', 'click both', 'left and right'],
         stands_for=['power-control.mp-switch-sound'],
         todo='站到两个电力开关正中间（牌子往南走到两个开关之间，面朝它们所在的那一排）。右键左边的开关一次（开）、再一次（关），再右键右边的开关两次；戴耳机或开立体声更容易分辨方位。每个开关各点两次，听清每一下。',
         expect='每一下右键响一声“反应堆启动”类的提示音：开的时候是正常音高，关的时候是同一个声音但明显更低沉（0.85 倍）；声音从被点的那个开关的方向传来（左边的开关声在左、右边的在右），距离近时音量清楚；一次点击只响一声，没有重叠或杂音。（专服上两名玩家都能听到那一半不在这里，归专服的人工站点。）',
         build=_switches, probe=_switches_probe, size=(9, 1, 3)),
]


def expectations():
    return S.station_expectations(STATIONS)
