"""Goal 32 user station for the basalt ores: mined with a Fortune and a Silk Touch pickaxe, the silk-touched ore placed back, and a
TNT among four of them. Built by stations.py; not run by drive.py.

Expected (original 1.7.10 / NEO):
- the five basalt ores (sulfur, fluorite, asbestos, gem, molysite) drop one sulfur, fluorite, asbestos sheet, volcanic gem or molysite
  each; the drop ignores Fortune (original BlockOreBasalt.java:32-45,55-59, ModBlocks.java:1321; NEO OreBasaltBlock.java:23-29 and its
  loot table, checked per subtype and tool by Goal32AGameTests.basalt_drops, Goal32AGameTests.java:225);
- Silk Touch drops the ore itself with its subtype: the 1.7.10 harvest path keeps the metadata in the dropped block item, and the item
  places the block with that metadata (original BlockOreBasalt extends BlockEnumMulti, :24-30; NEO the loot table's hbmsntm:meta and
  OreBasaltBlock.getStateForPlacement, OreBasaltBlock.java:31,46-50), so a silk-touched ore placed back looks like the one it came
  from: its own top and side textures (original :86-103; NEO blockstate ore_basalt, one model per subtype);
- an exploded ore drops what it drops when mined, with chance 1 / explosion size (TNT: 1/4) for each block (1.7.10
  Explosion.doExplosionB, dropBlockAsItemWithChance with 1 / explosionSize; NEO the loot table's survives_explosion);
- breaking the asbestos one leaves asbestos gas in its place (original :73-77; NEO OreBasaltBlock.java:68-71): it is in the row
  to look at only.
Textures and names are the person's to judge. The probe after the reload checks the rows, the loot of both pickaxes on the mining
rows (the loot command's `mine` with the tool) and that the silk-touch drop placed back by hand keeps its subtype.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _stations_g32 as S  # noqa: E402

SCENARIO = dict(
    id='materials.stations-g32',
    feature='materials',
    features=['world-generation'],
    title='Goal 32 station: basalt ores with Fortune and Silk Touch, the silk-touched ore placed back, TNT drops',
    group='station',
    station=True,
)

G, H = S.G, S.H
ORE = H + 'ore_basalt'
NAMES = ('sulfur', 'fluorite', 'asbestos', 'gem', 'molysite')          # subtype order, OreBasaltBlock.BasaltOreType
DROPS = (H + 'sulfur', H + 'fluorite', H + 'ingot_asbestos', H + 'gem_volcanic', H + 'powder_molysite')
MINED = (0, 1, 3, 4)                                                   # every subtype but asbestos
FORTUNE = 'minecraft:diamond_pickaxe[minecraft:enchantments={levels:{"minecraft:fortune":3}}]'
SILK = 'minecraft:diamond_pickaxe[minecraft:enchantments={levels:{"minecraft:silk_touch":1}}]'
LOOK_Z, FORTUNE_Z, SILK_Z, TNT_Z = 1, 3, 5, 13                         # rows, as z offsets from the station's z


def _chest_at(x, z):
    return (x + 10, G, z + 1)


def _tnt_cluster(x, z):
    """the TNT and the four ores around it: (TNT position, [(position, subtype)])"""
    tx, tz = x + 4, z + TNT_Z
    return (tx, G, tz), [((tx - 1, G, tz), 0), ((tx + 1, G, tz), 1), ((tx, G, tz - 1), 3), ((tx, G, tz + 1), 4)]


def _basalt(ctx, x, z):
    for sub in range(len(NAMES)):
        S.cmd(ctx, 'setblock %d %d %d %s[subtype=%d]' % (x + 2 * sub, G, z + LOOK_Z, ORE, sub))
    for row in (FORTUNE_Z, SILK_Z):
        for i, sub in enumerate(MINED):
            S.cmd(ctx, 'setblock %d %d %d %s[subtype=%d]' % (x + 2 * i, G, z + row, ORE, sub))
    # an obsidian pad under the TNT keeps the crater out of the ground (the reset clones from y = G up only)
    tnt, ores = _tnt_cluster(x, z)
    S.cmd(ctx, 'fill %d %d %d %d %d %d minecraft:obsidian' % (tnt[0] - 3, G - 1, tnt[2] - 3, tnt[0] + 3, G - 1, tnt[2] + 3))
    S.cmd(ctx, 'setblock %d %d %d minecraft:tnt' % tnt)
    for pos, sub in ores:
        S.cmd(ctx, 'setblock %d %d %d %s[subtype=%d]' % (pos + (ORE, sub)))
    cx, cy, cz = _chest_at(x, z)
    S.cmd(ctx, 'setblock %d %d %d minecraft:chest[facing=south]' % (cx, cy, cz))
    for slot, item in ((0, FORTUNE), (1, SILK), (2, 'minecraft:flint_and_steel')):
        S.cmd(ctx, 'item replace block %d %d %d container.%d with %s' % (cx, cy, cz, slot, item))


def _slot26(ctx, chest):
    """(item id, count, hbmsntm:meta or None) in the chest's last slot, read on the server"""
    text = S.block_data_text(ctx, chest, 'Items[{Slot:26b}]')
    item = re.search(r'id:\s*"([^"]+)"', text)
    count = re.search(r'\bcount:\s*(\d+)', text)
    meta = re.search(r'"hbmsntm:meta":\s*(\d+)', text)
    return (item.group(1) if item else None, int(count.group(1)) if count else None, int(meta.group(1)) if meta else None)


def _basalt_probe(ctx, x, z):
    chest = _chest_at(x, z)
    d = ctx.step('dump', **{'from': [x, G, z + LOOK_Z], 'to': [x + 8, G, z + TNT_Z + 1]})
    seen = {tuple(int(c) for c in b['pos']): int(b['props'].get('subtype', -1)) for b in d['blocks'] if b['block'] == ORE}
    want = {(x + 2 * sub, G, z + LOOK_Z): sub for sub in range(len(NAMES))}
    for row in (FORTUNE_Z, SILK_Z):
        want.update({(x + 2 * i, G, z + row): sub for i, sub in enumerate(MINED)})
    want.update({pos: sub for pos, sub in _tnt_cluster(x, z)[1]})
    rows_ok = seen == want
    loot, bad = {}, []
    for i, sub in enumerate(MINED):
        for row, tool, label in ((FORTUNE_Z, FORTUNE, 'fortune'), (SILK_Z, SILK, 'silk')):
            S.cmd(ctx, 'item replace block %d %d %d container.26 with minecraft:air' % chest)
            S.cmd(ctx, 'loot replace block %d %d %d container.26 mine %d %d %d %s' % (chest + (x + 2 * i, G, z + row, tool)))
            got = _slot26(ctx, chest)
            loot['%s %s' % (label, NAMES[sub])] = got
            expect = (DROPS[sub], 1) if label == 'fortune' else (ORE, 1)
            if got[:2] != expect or (label == 'silk' and (got[2] or 0) != sub):
                bad.append((label, NAMES[sub], got))
    # the silk-touch drop of the gem ore, from the chest into the hand, placed on the ground by a right-click
    S.cmd(ctx, 'item replace block %d %d %d container.26 with minecraft:air' % chest)
    S.cmd(ctx, 'loot replace block %d %d %d container.26 mine %d %d %d %s' % (chest + (x + 4, G, z + SILK_Z, SILK)))
    S.cmd(ctx, 'item replace entity @s weapon.mainhand from block %d %d %d container.26' % chest)
    spot = (x + 10, G, z + 9)
    S.use_face(ctx, (spot[0], G - 1, spot[2]), 'up', [spot[0] + 0.5, G, spot[2] + 2.5])
    ctx.step('wait', ticks=4)
    placed = ctx.step('dump', **{'from': list(spot)})['blocks']
    placed_sub = int(placed[0]['props'].get('subtype', -1)) if placed and placed[0]['block'] == ORE else None
    S.clear_hand(ctx)
    S.cmd(ctx, 'setblock %d %d %d minecraft:air' % spot)
    S.cmd(ctx, 'item replace block %d %d %d container.26 with minecraft:air' % chest)
    ok = rows_ok and not bad and placed_sub == 3
    return ok, 'rows as built %s (differences %s); loot (item, count, meta) %s, wrong %s; silk-touched gem ore placed back: subtype %s, want 3' % (
        rows_ok, {k: (seen.get(k), v) for k, v in want.items() if seen.get(k) != v}, loot, bad, placed_sub)


STATIONS = [
    dict(id='materials.station-basalt-precise-place', short=['BASALT ORE', 'fortune+silk', 'place back,TNT'],
         stands_for=[],
         todo='先输入 /gamemode survival（创造模式挖方块不掉东西）。从箱子里拿出时运 III 钻石镐、精准采集钻石镐和打火石。'
              '第一排（离牌子最近，五块）只看不挖：五种玄武岩矿各自的顶面与侧面（石棉那块挖开会变成石棉气体，不要挖）。'
              '用时运镐挖第二排四块，捡起掉落看是什么、几个。用精准采集镐挖第三排四块，捡起的方块悬停看名字，再把四块各放回地上，'
              '和第一排同种的那块比外观。然后输入 /gamemode creative（爆炸的掉落与游戏模式无关，创造模式下不会被炸伤）。'
              '走到南边黑曜石台上，用打火石点燃中间的 TNT，退到 8 格外，炸完回去看地上的掉落。'
              '要重做先按复位按钮（TNT 一次可能什么也不掉，复位后再炸一次）。',
         expect='时运镐挖的每块只掉一个对应的东西（硫粉、氟石粉、火山宝石、氯化铁），时运不让数量变多；精准采集挖下的是矿石本身，'
                '名字分别是“富含硫的玄武岩”“富含氟石的玄武岩”“富含宝石的玄武岩”“富含氯化铁的玄武岩”，放回地上的四块各自和第一排同种的那块'
                '顶面、侧面都一样（不会都变成同一种或变成普通玄武岩，没有紫黑方块）；TNT 炸掉的四块里每块约四分之一的机会掉东西，'
                '掉的是上面那些产物、不是矿石本身，一次可能一个也不掉。',
         build=_basalt, probe=_basalt_probe, size=(11, 1, 15)),
]


def expectations():
    return S.station_expectations(STATIONS)
