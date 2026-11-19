"""Goal 32 user station for the foundry mold block and the basin: the plug sound when a mold goes in, and the solid half-block
outline of the small mold. Built by stations.py; not run by drive.py.

Expected (original 1.7.10 / NEO):
- a held mold of the block's size goes into an empty, unfilled casting block and "hbm:item.upgradePlug" plays at the block's
  centre at volume 1.0, pitch 1.0 (original FoundryCastingBase.java:105; NEO FoundryCastingBlock.java:60-66, played on the server);
  a mold of the other size does nothing: no sound, the block stays empty (original :101-108, size check on both sides);
- the small mold block's selection outline is the solid box 0..0.5 high (original FoundryMold.java:65-66 setBlockBounds
  0, 0, 0, 1, 0.5, 1; NEO FoundryMoldBlock.java:17-18,25), while its hollow shape is the collision only.
Whether the sound is heard and sounds right, and whether the outline looks right, is the person's call.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _stations_g32 as S  # noqa: E402

SCENARIO = dict(
    id='foundry-casting.stations-g32',
    feature='foundry-casting',
    title='Goal 32 station: foundry mold insert sound (small and large) and the small mold outline',
    group='station',
    station=True,
)

G = S.G
MOLD, BASIN = 'hbmsntm:mold_ingot', 'hbmsntm:mold_ingots'


def _molds(ctx, x, z):
    # the small mold block (size 0) at x + 1 and the basin (size 1) at x + 4, a chest of molds in front of them
    S.cmd(ctx, 'setblock %d %d %d hbmsntm:foundry_mold' % (x + 1, G, z + 1))
    S.cmd(ctx, 'setblock %d %d %d hbmsntm:foundry_basin' % (x + 4, G, z + 1))
    S.chest(ctx, x + 2, z + 4, [(0, MOLD, 1), (1, BASIN, 1)])


def _molds_probe(ctx, x, z):
    """puts each mold into its own block like a player and records the plug sounds; then the large mold into the small block (nothing)"""
    small, large = (x + 1, G, z + 1), (x + 4, G, z + 1)
    aim = [0.0, -0.3, -0.45]
    ctx.step('sounds', action='start')
    S.hold_item(ctx, MOLD)
    h1 = (S.use_face(ctx, small, 'south', [x + 1.5, G, z + 3.5], offset=aim, after=10).get('hit') or {}).get('pos')
    S.hold_item(ctx, BASIN)
    h2 = (S.use_face(ctx, large, 'south', [x + 4.5, G, z + 3.5], offset=aim, after=10).get('hit') or {}).get('pos')
    ctx.step('wait', ticks=6)
    plugs = S.sounds_of(ctx.step('sounds', action='stop'), 'upgrade_plug')
    S.clear_hand(ctx)
    t_small, t_large = S.block_data_text(ctx, small), S.block_data_text(ctx, large)
    ok = (len(plugs) == 2 and h1 == list(small) and h2 == list(large) and 'mold_ingot' in t_small and 'mold_ingots' in t_large)
    return ok, ('plug sounds %d (want 2); hits %s %s; small block holds mold_ingot %s, basin holds mold_ingots %s'
                % (len(plugs), h1, h2, 'mold_ingot' in t_small, 'mold_ingots' in t_large))


STATIONS = [
    dict(id='foundry-casting.station-mold-sound', short=['MOLD PLUG', 'mold in hand', 'right-click'],
         stands_for=[],
         todo='箱子里有一个小模具（锭模）和一个大模具（多锭模）。拿出小模具拿在手里，右键左边较矮的“铸模台”；再拿大模具右键右边较宽的“铸造盆”。听每一下。然后试错的：拿大模具右键铸模台（小块），再拿小模具右键铸造盆。最后空手把准星对着铸模台，看黑色选取框。（要重做先按复位按钮；已放进去的模具用螺丝刀可以取出。）',
         expect='模具放进尺寸对得上的块时响一声清脆的“咔”（插头声，与升级插件的声音一样），一次一声；尺寸对不上时没有声音、模具也进不去；铸模台的选取框是一个实心的半格高方框（不是只有一圈边的空盆形状）。',
         build=_molds, probe=_molds_probe, size=(6, 1, 5)),
]


def expectations():
    return S.station_expectations(STATIONS)
