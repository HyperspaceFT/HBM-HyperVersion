"""Dedicated server: the sounds a person has to hear (switch clicks, the small explosion of a congested conveyor).

The executor records sound events but cannot say whether a sound is heard right, in the right place and at the right volume, and
the clients' audio is not checked by the tools; these rows belong to the user's station and are not run here.

Expected (original 1.7.10 / NEO):
- a cable switch plays the reactor-start sound at pitch 1.0 when switched on and 0.85 when switched off, sent by the server to
  the players near it (original CableSwitch.java:52,55; NEO CableSwitchBlock.java:63);
- moving conveyor objects crammed together at or above the congestion limit (25 by default) pop with a small explosion and its
  sound (original ServerConfig.java:29-30, EntityMovingConveyorObject.java:88-97; NEO MovingConveyorObject.java:173-187).
"""
SCENARIO = dict(
    id='power-control.mp_sounds',
    feature='power-control',
    features=['conveyors'],
    title='Dedicated server: switch sounds and the congestion explosion sound (user station, not run)',
    group='mp',
    capture=dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70),
)

REASON = '只能人听：声音的有无、方位与音量要用户在专服上的两个客户端里听，执行器只记录声音事件，归用户站点'
EXPECT = [
    ('power-control.mp-switch-sound', '专服上拨动电力开关：两名玩家都听到开关声（开时音调 1.0、关时 0.85），各自的方位正确', 'CableSwitch.java:52,55; CableSwitchBlock.java:63'),
    ('conveyors.mp-cram-explosion-sound', '专服上传送带拥堵达到上限（默认 25）时的小爆炸：两名玩家都听到爆炸声', 'ServerConfig.java:29-30, EntityMovingConveyorObject.java:88-97; MovingConveyorObject.java:173-187'),
]


def expectations():
    return [dict(id=i, text=t, source=s) for i, t, s in EXPECT]


def run(ctx):
    for eid, _, _ in EXPECT:
        ctx.not_run(eid, REASON)
