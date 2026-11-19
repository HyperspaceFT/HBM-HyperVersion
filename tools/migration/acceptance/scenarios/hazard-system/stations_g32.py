"""Goal 32 user station for the radiation fog of a contaminated chunk. Built by stations.py; not run by drive.py.

Expected (original 1.7.10 / NEO): a chunk whose radiation is above the fog threshold spawns radiation fog particles inside that
chunk, at a random block of the chunk and up to four blocks above the surface, one in `fogCh` chances a second; the radiation also
leaks into the eight neighbouring chunks, so the fog spreads to them while it lasts (original ChunkRadiationHandlerSimple.java:95-115;
NEO ChunkRadiationHandlerSimple.java:97-115, particle RADIATION_FOG). The command /ntmchunkrad set <rad> sets the radiation of the
chunk the player stands in (NEO ChunkRadCommand.java:18-39). The fog needs more than fogRad = 100 (CommonConfig.java:456-459) and
1 in fogRadChance = 20 (:460-463) each second; the radiation spreads and decays every second, so a high value (10000) lasts about ten seconds.
Whether the fog looks right and sits in the right chunk is the person's call. The station is a floor marking: the chunk is reset by
waiting or by setting the radiation back to 0, not by the reset button (which clones blocks).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _stations_g32 as S  # noqa: E402

SCENARIO = dict(
    id='hazard-system.stations-g32',
    feature='hazard-system',
    title='Goal 32 station: radiation fog in a contaminated chunk',
    group='station',
    station=True,
)

G = S.G


def _fog(ctx, x, z):
    # four white wool markers at the corners of the station's own 12 x 12 block patch, and a sea lantern in the middle to find it by
    for dx, dz in ((0, 0), (11, 0), (0, 11), (11, 11)):
        for dy in range(3):
            S.cmd(ctx, 'setblock %d %d %d minecraft:white_wool' % (x + dx, G + dy, z + dz))
    S.cmd(ctx, 'setblock %d %d %d minecraft:sea_lantern' % (x + 6, G - 1, z + 6))


STATIONS = [
    dict(id='hazard-system.station-chunk-fog', short=['CHUNK FOG', 'type command', 'F3+G borders'],
         stands_for=[],
         todo='站在白羊毛柱围出的区域中间，打开聊天输入 /ntmchunkrad set 10000（把脚下这个区块的辐射设成 10000；雾要辐射高于 100 才出，辐射每秒向四周扩散衰减，过十几秒雾停了就再输一次；创造模式不受辐射伤害，别切到生存）。按 F3+G 显示区块边界，沿边界走一圈。看灰绿色的雾粒子出现在哪里、持续多久。看完输入 /ntmchunkrad set 0，或者等它自己散去。',
         expect='设置后几秒内，所在区块里（蓝色的区块边界线之内）的地面上方出现灰绿色的雾粒子，离地面不超过几格；辐射向相邻区块泄漏时，邻近区块里也会稀疏地出现雾，较远的区块没有；设回 0 之后雾逐渐停止。雾的位置对得上区块（不是只在你脚边，也不是整片天空）。',
         build=_fog, size=(12, 3, 12)),
]


def expectations():
    return S.station_expectations(STATIONS)
