"""Goal 32 user station for the small explosion of a congested belt: its sound, heard in single player. Built by stations.py; not
run by drive.py. The ring, the two extractors and the probe are Goal 31's (stations_g31.py), which ran on a built world before;
only the question changes: this station asks about the sound.

Expected (original 1.7.10 / NEO): 25 or more moving belt objects within one object's reach (ServerConfig.java:29-30,
EntityMovingConveyorObject.java:88-97; NEO MovingConveyorObject.java:173-187) are removed together with a tiny explosion
(ExplosionEffectTiny: a small bang, a puff of smoke) that hurts nothing; the belt under the checking object goes too when it is
old enough. The recorded sound event is the tiny explosion's; whether it is heard in the right place and at the right volume is
the person's call.
"""
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location('conveyors_stations_g31', Path(__file__).resolve().with_name('stations_g31.py'))
G31 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(G31)

SCENARIO = dict(
    id='conveyors.stations-g32',
    feature='conveyors',
    title='Goal 32 station: the small bang of a congested belt, heard',
    group='station',
    station=True,
)

STATIONS = [
    dict(id='conveyors.station-cram-sound', short=['CRAM SOUND', 'flip lever', 'listen'],
         stands_for=['conveyors.mp-cram-explosion-sound'],
         todo='站在环旁 4 到 6 格处（不要贴着环），扳一下两台提取器中间的拉杆（关掉红石，两台提取器开始往一个封闭的小环上快速送圆石）。环上的物品越积越密，十来秒后在某一处挤满，听那一声爆炸。约 1 分钟还没响，就退出世界再进来接着等。再试一次可以按复位按钮。',
         expect='挤满的那一刻响一声小而短的爆炸声（不是 TNT 那样的大声），从环上出事的那个位置传来，同时冒出一团烟，那一堆物品消失；一声就是一声，不连响；环附近的方块和人不受伤。声音的方向和距离感对得上爆炸的位置。（专服上两名玩家都能听到那一半不在这里。）',
         build=G31._cram, probe=G31._cram_probe, size=(3, 2, 5)),
]


def expectations():
    return [dict(id=s['id'], text=s['expect'], source='user station; stands for ' + ', '.join(s['stands_for'])) for s in STATIONS]
