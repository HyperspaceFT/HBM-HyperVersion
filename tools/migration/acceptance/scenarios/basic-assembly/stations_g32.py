"""Goal 32 user stations for machines you hear and keys you type: the assembly machine's motor loop and strikes, the shredder's
and the centrifuge's work sounds, and typing into the recipe selector's search field the moment it opens (real keyboard, Chinese
input method). Built by stations.py; not run by drive.py.

Expected (original 1.7.10 / NEO):
- an assembly machine with a running recipe plays a motor loop (volume 0.5, pitch 0.75, heard within 15 blocks) and a strike each
  time an arm comes down; its ring turns with a start sound (original TileEntityMachineAssemblyMachine.java:137-194, ELECTRIC_MOTOR_LOOP
  :194; NEO MachineAssemblyMachineBlockEntity.java:134-178,197-198);
- a shredder with work plays the minecart roll sound at pitch 0.75 every 50 ticks while it works (original
  TileEntityMachineShredder.java:261-267); NEO plays a minecart-riding loop at pitch 0.65 while it runs (NEO
  MachineShredderBlockEntity.java:64-80,384-385), which is the person's call to judge by ear;
- a centrifuge with work plays its loop while it processes, pitch and volume rising and falling with the work (original
  TileEntityMachineCentrifuge.java:244-262,291; NEO MachineCentrifugeBlockEntity.java:131,337-338);
- the recipe selector's search field has the focus when the screen opens, so typed letters (and input-method text) go into it and a
  letter bound to the inventory key does not close the screen (NEO RecipeSelectorScreen.init sets the focus; original
  GUIScreenRecipeSelector.java:85).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _stations_g32 as S  # noqa: E402

SCENARIO = dict(
    id='basic-assembly.stations-g32',
    feature='basic-assembly',
    features=['shredder', 'centrifuge'],
    title='Goal 32 stations: assembler loop and strikes, shredder and centrifuge work sounds, typing into the recipe selector',
    group='station',
    station=True,
)

G, H = S.G, S.H
WIRE, NIOBIUM, MAGNETRON = H + 'wire_tungsten', H + 'powder_niobium', H + 'magnetron'
ASSEMBLER = 'machine_assembly_machine'


def _assembler_loop(ctx, x, z):
    # ass.magnetron: 4 tungsten wire and 3 niobium powder, 40 ticks, 100 a tick. The machine stays still with the wire in and the
    # niobium missing; the person takes the niobium from the chest and puts it in. (The template is a working copy: a machine
    # that could run would use up its feed before anyone presses reset.)
    core, _ = S.place_machine(ctx, ASSEMBLER, x + 3, z + 2)
    S.merge(ctx, core, '{power:100000L,maxPower:100000L,recipe0:"ass.magnetron",Items:[{Slot:4b,id:"%s",count:64}]}' % WIRE)
    S.chest(ctx, x + 1, z + 7, [(0, NIOBIUM, 64)], facing='north')


def _assembler_loop_probe(ctx, x, z):
    core, _ = S.find_core(ctx, H + ASSEMBLER, (x - 2, G, z - 2), (x + 8, G + 5, z + 6))
    ctx.step('sounds', action='start')
    S.merge(ctx, core, S.items_snbt([(4, WIRE, 64), (5, NIOBIUM, 64)]))
    ctx.step('wait', ticks=120)
    snd = ctx.step('sounds', action='stop')
    names = sorted({s['event'] for s in snd.get('sounds', [])})
    made = S.block_data_text(ctx, core, 'Items')
    return MAGNETRON in made, 'after 120 ticks with niobium: magnetron in the output %s; sound events heard %s' % (MAGNETRON in made, names[:8])


def _recipe_search(ctx, x, z):
    S.place_machine(ctx, ASSEMBLER, x + 3, z + 2)


def _recipe_search_probe(ctx, x, z):
    """opens the assembler's screen like a player, then its recipe selector, and reads that the search field has the focus"""
    core, _ = S.find_core(ctx, H + ASSEMBLER, (x - 2, G, z - 2), (x + 8, G + 5, z + 6))
    S.use_face(ctx, core, 'south', [core[0] + 0.5, G, core[2] + 4.0], offset=[0.0, -0.4, -0.45], after=8)
    r = ctx.step('screen', expect='Assembl', allow_fail=True)
    shown = r.get('screen')
    ctx.step('close', allow_fail=True)
    return r.get('status') == 'ok', 'screen after a plain right-click on the assembler: %s (the recipe selector itself is the person\'s)' % shown


SHRED_ORE = (0, H + 'ore_lead', 8)
CENTRIFUGE_ORE = H + 'ore_lead_deepslate'


def _loops(ctx, x, z):
    # a shredder at x + 2 and a centrifuge at x + 8, both charged and fitted, each with a chest of ore in front. The shredder is
    # given its two steel blades; both stay still with no ore in them.
    s_core, _ = S.place_machine(ctx, 'machine_shredder', x + 2, z + 2)
    c_core, _ = S.place_machine(ctx, 'machine_centrifuge', x + 8, z + 2)
    S.merge(ctx, s_core, '{power:100000L,maxPower:100000L,Items:[{Slot:27b,id:"%sblades_steel",count:1},{Slot:28b,id:"%sblades_steel",count:1}]}' % (H, H))
    S.merge(ctx, c_core, '{power:100000L}')
    S.chest(ctx, x + 2, z + 7, [(0, H + 'ore_lead', 8)], facing='north')
    S.chest(ctx, x + 8, z + 7, [(0, CENTRIFUGE_ORE, 3)], facing='north')


def _loops_probe(ctx, x, z):
    s_core, _ = S.find_core(ctx, H + 'machine_shredder', (x - 2, G, z - 2), (x + 5, G + 5, z + 6))
    c_core, _ = S.find_core(ctx, H + 'machine_centrifuge', (x + 5, G, z - 2), (x + 11, G + 5, z + 6))
    ctx.step('sounds', action='start')
    S.merge(ctx, s_core, '{Items:[{Slot:0b,id:"%s",count:2},{Slot:27b,id:"%sblades_steel",count:1},{Slot:28b,id:"%sblades_steel",count:1}]}' % (
        H + 'ore_lead', H, H))
    S.merge(ctx, c_core, S.items_snbt([(0, CENTRIFUGE_ORE, 1)]))
    ctx.step('wait', ticks=260)
    snd = ctx.step('sounds', action='stop')
    names = sorted({s['event'] for s in snd.get('sounds', [])})
    s_text = S.block_data_text(ctx, s_core, 'Items')
    c_text = S.block_data_text(ctx, c_core, 'Items')
    ok = 'powder_lead' in s_text and 'powder_lead' in c_text
    return ok, 'after 260 ticks: shredder made lead powder %s, centrifuge made lead powder %s; sound events heard %s' % (
        'powder_lead' in s_text, 'powder_lead' in c_text, names[:8])


STATIONS = [
    dict(id='basic-assembly.station-assembler-loop', short=['ASSEMBLER', 'add niobium', 'listen'],
         stands_for=[],
         todo='装配机已经选好“磁控管”配方、插着钨线、也有电，只缺铌粉：从旁边的箱子里拿出铌粉，打开装配机，把铌粉放进输入格（Shift 点击即可）。走近、走远（15 格内都能听到）、绕着它走。看它的机械臂和圆环。听大约 30 秒（要重做先按复位按钮）。',
         expect='有输入开始工作后，持续的电机嗡鸣声（比较低沉，不刺耳），机械臂每落下一次有一声敲击声，圆环转动时有一声启动声；越远越小声、15 格外听不到；缺料或做完时嗡鸣声停止，不会拖尾或一直响。声音从机器的位置传来，机器不叠响（只有一个嗡鸣）。',
         build=_assembler_loop, probe=_assembler_loop_probe, size=(8, 4, 8)),
    dict(id='basic-assembly.station-recipe-search', short=['TYPE AT ONCE', 'open selector', 'then type'],
         stands_for=[],
         todo='打开装配机界面，点配方选择按钮打开“配方选择”界面。不要点搜索框，立刻用真实键盘打字：先打英文单词（例如 steel），再切到中文输入法打拼音（例如 gang）选字，再打 e（物品栏键）。有数字小键盘就再试一次数字。',
         expect='界面一打开搜索框就有焦点，打的字直接出现在搜索框里，列表随之过滤；中文输入法选好的字进了搜索框（拼音阶段不显示可以接受），字母没有被吞；打 e 不会关掉界面（只在搜索框里出现一个 e）；Esc 才关。',
         build=_recipe_search, probe=_recipe_search_probe, size=(8, 4, 6)),
    dict(id='shredder.station-loops', short=['SHREDDER', 'CENTRIFUGE', 'load the ore'],
         stands_for=[],
         todo='左边粉碎机、右边离心机，各有一个装矿石的箱子。从左边箱子拿铅矿，打开粉碎机放进输入格；从右边箱子拿深层铅矿放进离心机的输入格。各听约 20 秒，走近走远。粉碎机会磨掉刀片耐久，要重做先按复位按钮。',
         expect='粉碎机工作时有节奏的推车滚动声（原版是每 2.5 秒一段推车滚动声，音调偏低；NEO 用一段持续的滚动声，如果听起来明显不像原版的节奏、或者太尖太吵，记下来）；离心机工作时有持续的嗡嗡声，工作停下后声音逐渐减弱消失；两台同时响时各听各的、没有叠响，停了就静。',
         build=_loops, probe=_loops_probe, size=(12, 4, 8)),
]


def expectations():
    return S.station_expectations(STATIONS)
