"""Dedicated server: a machine recipe file whose output items carry NBT strings, one of them broken, read at a server restart.

The scenario writes a one-off blast furnace recipe file (hbmBlastFurnace.json, the name without the template's underscore, so it is
read instead of the defaults) into the server's config/hbmRecipes, restarts the server on the same world and reads the server log;
A then places a blast furnace by hand and runs each recipe in the frozen world with tick steps. The file is removed again when the
run's server stops (the run directory is restored from its backup).

Recipes in the file (inputs iron ingot + X, duration 16, output item array [id, count, meta, NBT string]):
- "{broken:"  (iron + sand -> stick): does not parse;
- "5b"        (iron + gravel -> string): valid NBT, but a byte, not a compound;
- "{probe:1b}"  (iron + red sand -> paper): parses to a compound.

Expected (original 1.7.10 / NEO):
- a recipe item array's fourth entry is passed to ItemStackUtil.addNBTFromString (original SerializableRecipe.java:326-338;
  NEO SerializableRecipe.java:357-367), here through the generic "single" output of the blast furnace recipe (original
  GenericRecipes.java:276-279; NEO GenericRecipes.java:269-272);
- addNBTFromString parses the string and puts it on the item only when it is a compound; a string that does not parse throws the
  parser's own exception, which is caught and ignored (original ItemStackUtil.java:242-251, catch NBTException; NEO
  ItemStackUtil.java:157-164, catch CommandSyntaxException, custom data through TagsUtil.putCustomData), so the recipe loads and its
  item is made without data. "5b": the original parser returns a byte tag, which the compound check drops (original
  ItemStackUtil.java:245-247); the 1.21.1 parser behind NEO's call (TagParser.parseTag -> readSingleStruct) reads only a compound
  and throws CommandSyntaxException, which the same catch ignores: the item is made without data either way; nothing reaches readItemStack's own catch, so no "Error reading stack array" line (NEO
  SerializableRecipe.java:365-366) and no skipped row or rejected file (NEO SerializableRecipe.java:255-257,280-281,132-133);
- the file is read when it exists and its rows replace the defaults (original SerializableRecipe.java:142-145; NEO
  SerializableRecipe.java:126-131);
- a blast furnace recipe advances speed / duration a tick, speed 1 with an empty air tank (max(1, min(5, 1 + 0 * 8 / max))), and
  finishes when progress reaches 1: a duration of 16 finishes on its 16th tick (NEO MachineBlastFurnaceBlockEntity.java:77-92);
  coal in the fuel slot is burnt in the same tick before the recipe check (NEO MachineBlastFurnaceBlockEntity.java:75,108-119).
"""
import importlib.util
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _lib  # noqa: E402
import common  # noqa: E402

_spec = importlib.util.spec_from_file_location('automation_mp', Path(__file__).resolve().parents[1] / 'machine-item-capability' / 'mp_automation.py')
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)
Z = M.Z

SCENARIO = dict(
    id='goal30-fixes.mp_item_nbt_string',
    feature='goal30-fixes',
    title='Dedicated server: recipe file with a broken NBT string read at a restart (log, recipes made with and without data)',
    group='mp',
    capture=dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70),
)

G = _lib.FLAT_FEET
H = _lib.H
GF = 'goal30-fixes.'
FURNACE = (40, 140)
RECIPE_FILE = 'hbmBlastFurnace.json'
DURATION = 16
# (name, second input, output item, NBT string, custom data expected on the output)
RECIPES = [
    ('blast.nbtBroken', 'minecraft:sand', 'minecraft:stick', '{broken:', None),
    ('blast.nbtScalar', 'minecraft:gravel', 'minecraft:string', '5b', None),
    ('blast.nbtGood', 'minecraft:red_sand', 'minecraft:paper', '{probe:1b}', {'probe': 1}),
]
ERRORS = re.compile(r'Unable to load recipe file|Skipping invalid recipe|Error reading stack array|Falling back to default recipes')
SRC_PARSE = 'ItemStackUtil.java:242-251, SerializableRecipe.java:326-338; ItemStackUtil.java:157-164, SerializableRecipe.java:357-367'
EXPECT = [
    ('mp-item-nbt-load', '专服重启时读脚本写进 run/config/hbmRecipes 的一次性高炉配方文件（三条配方，NBT 字符串 "{broken:"、"5b"、"{probe:1b}"）照常启动：'
     '日志有读这个文件的行，没有“Unable to load recipe file”“Skipping invalid recipe”“Error reading stack array”“Falling back to default recipes”',
     SRC_PARSE + ', SerializableRecipe.java:126-133,255-257,280-281'),
    ('mp-item-nbt-bad', '坏 NBT 字符串 "{broken:" 的配方（铁锭 + 沙子 → 木棍，时长 16）照样生效：冻结后走 15 刻没有产物，第 16 刻出 1 根木棍，木棍不带自定义数据',
     SRC_PARSE + ', MachineBlastFurnaceBlockEntity.java:77-92'),
    ('mp-item-nbt-scalar', '不是复合标签的 NBT 字符串 "5b" 的配方（铁锭 + 沙砾 → 线，时长 16；原版解析成字节标签后丢掉，NEO 的解析器只读复合标签、抛出的语法异常被同一个捕获忽略）：第 15 刻没有产物，第 16 刻出 1 根线，不带自定义数据',
     'ItemStackUtil.java:245-247; ItemStackUtil.java:160-162, MachineBlastFurnaceBlockEntity.java:77-92'),
    ('mp-item-nbt-good', '对照：NBT 字符串正确的配方（铁锭 + 红沙 → 纸，"{probe:1b}"，时长 16）第 15 刻没有产物，第 16 刻出 1 张带自定义数据 {probe:1b} 的纸',
     SRC_PARSE + ', MachineBlastFurnaceBlockEntity.java:77-92'),
    ('mp-item-nbt-restore', '这份一次性配方文件在专服停下时随 run/ 的还原删掉（server.py stop 的还原报告与哈希核对），由运行之后核对',
     'server.py stop'),
]


def expectations():
    return [dict(id=GF + k, text=t, source=s) for k, t, s in EXPECT]


def recipe_json():
    return dict(recipes=[dict(name=name, inputItem=[['item', 'minecraft:iron_ingot', 1, 32767], ['item', second, 1, 32767]],
                              outputItem=[['single', [out, 1, 0, nbt]]], duration=DURATION)
                         for name, second, out, nbt, _ in RECIPES])


def run(ctx):
    a, b = list(ctx.channels)
    Z.setup_world(ctx, a, b)
    ctx.rcon('tick unfreeze')
    S = {}

    def restart():
        config = Path((common.read_json(common.SESSION) or {})['run']) / 'config' / 'hbmRecipes'
        target = config / RECIPE_FILE
        if target.exists():
            raise RuntimeError('%s exists before the scenario writes it' % target)
        config.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(recipe_json(), indent=2) + '\n', encoding='utf-8')
        S['mark'] = Z.log_mark()
        ctx.step('close', client=b, allow_fail=True)
        _lib.reopen(ctx, who=a)
        _lib.server_idle(ctx, a)
        lines, logs = Z.log_lines(S['mark'])
        text = '\n'.join(lines)
        read = [ln[:160] for ln in lines if RECIPE_FILE in ln and 'Reading recipe file' in ln]
        bad = [ln[:200] for ln in lines if ERRORS.search(ln)]
        ctx.check(GF + 'mp-item-nbt-load', bool(read) and not bad and 'Done (' in text,
                  'file written %s; log %s: reading lines %s; error lines %s; server started %s'
                  % (common.rel(target), ', '.join(logs), read, bad[:4], 'Done (' in text), ['server log'])
    _lib.section(ctx, [GF + r[0] for r in EXPECT[:4]], restart, 'restart with the recipe file')

    def recipes():
        x, z = FURNACE
        ctx.rcon('fill %d %d %d %d %d %d minecraft:air' % (x - 4, G, z - 4, x + 4, G + 7, z + 4), 'kill @e[type=minecraft:item]')
        core = Z.place_by_hand(ctx, a, H + 'machine_blast_furnace', x, z, H + 'machine_blast_furnace', ((x - 3, G, z - 3), (x + 3, G + 6, z + 3)))
        cells = M.cells_of(ctx, a, H + 'machine_blast_furnace', (x - 3, G, z - 3), (x + 3, G + 6, z + 3))
        view = M.opener(M.south_cell(cells), expect='MachineBlastFurnaceScreen')
        ctx.server('tick freeze')
        M.give(ctx, a, ('minecraft:coal', 3))
        M.open_(ctx, a, view)
        M.put(ctx, a, 5, 'minecraft:coal', 0)
        for (name, second, out, nbt, data), key in zip(RECIPES, ('mp-item-nbt-bad', 'mp-item-nbt-scalar', 'mp-item-nbt-good')):
            ctx.step('close', client=a)
            M.give(ctx, a, ('minecraft:iron_ingot', 1), (second, 1))
            M.open_(ctx, a, view)
            M.put(ctx, a, 5, 'minecraft:iron_ingot', 1)
            M.put(ctx, a, 5, second, 2)
            before = M.custom_data(ctx, core, 3)
            _lib.server_steps(ctx, DURATION - 1)
            at15 = M.custom_data(ctx, core, 3)
            _lib.server_steps(ctx, 1)
            at16 = M.custom_data(ctx, core, 3)
            ctx.check(GF + key, before is None and at15 is None and at16 == (out, 1, data),
                      '%s, NBT string %r: slot 3 before %s, after %d ticks %s, after %d: %s (id, count, custom data)'
                      % (name, nbt, before, DURATION - 1, at15, DURATION, at16), ['rcon log'])
            if at16 is not None:
                Z.shift_click(ctx, a, 3)
            ctx.rcon('clear %s' % a)
        ctx.step('close', client=a)
        ctx.rcon('clear %s' % a, 'tick unfreeze')
    if 'mark' in S:
        _lib.section(ctx, [GF + r[0] for r in EXPECT[1:4]], recipes, 'recipes')
    ctx.review(GF + 'mp-item-nbt-restore', 'decided after the run: the restore runs in server.py stop after every scenario has ended, so '
               'no scenario can read its result; its restore report (removed_new_config_files lists %s, mismatched empty) and a hash '
               'check of run/config against the state before the run decide this row' % RECIPE_FILE, [])
    _lib.server_idle(ctx, a)
