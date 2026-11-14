"""Settings tool: recipe, item, tooltips, copy messages, and pastes that survive leaving the world without opening a screen.

Expected values follow the 1.7.10 original at cd0cff450:
- recipe " P ", "PCP", "III" with P iron plate, C analog circuit, I polymer plate (ToolRecipes.java:124); not stackable
  (ItemSettingsTool, maxStackSize 1).
- tooltip (ItemSettingsTool.addInformation): three description lines, then the copied machine's name; a new tool has only
  the three lines (" none " needs data without a source name, which play does not produce).
- sneak-use copies (chat "[Settings Tool] copied ... settings"); on a block without settings the tool passes: no message,
  the stored data stays (ItemSettingsTool.onItemUse); use pastes.
- the pasted values are kept by the world: after a paste with no screen opened, leaving and reopening the world shows them
  (the NEO marks the target for saving after a paste; IFluidCopiable / ICopiable paste paths).
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _lib  # noqa: E402

SCENARIO = dict(
    id='settings-tool.paste',
    feature='settings-tool',
    title='Settings tool: recipe, item, tooltips, copy messages, pastes kept after reopening the world',
    group='solo',
    capture=dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70, hide_gui=True),
)

Y = -60
OX = 1000
T = dict(zh_cn=dict(desc=['可以复制机器的设置（过滤器、流体类型等）', '潜行右键复制，右键粘贴', '按住Ctrl点击管道可将设置粘贴到相连的多段管道'], none=' 无 ',
                    copied='已复制', failed='复制失败，该机器不支持设定工具'),
         en_us=dict(desc=['Can copy the settings', 'Shift right-click to copy', 'Ctrl'], none=' None ', copied='Copied', failed='Copy failed'))
# block, source settings (data merge), keys compared after the paste
MACHINES = [('heater_electric', '{setting:7}', ['setting']),
            ('heater_heatex', '{toCool:250,delay:3}', ['toCool', 'delay']),
            ('machine_battery_socket', '{RedLow:2s,RedHigh:3s}', ['RedLow', 'RedHigh']),
            ('barrel_steel', '{tank_type:"WATER"}', ['tank_type'])]


# the 6.1 families beyond paste-reload: block placed with setblock (a multiblock's core alone carries the block entity that
# copies and pastes), source data, the entry to paste (1 is chosen with the real Alt key), what is read back on the server
FAMILIES = [
    dict(name='inserter', block='crane_inserter', src='[input=east,output=west]', merge=None, index=1, state='[input=east,output=west]',
         text='inserter: entry 1 (orientation) pastes input east, output west', source='TileEntityCraneBase.java:140-176'),
    dict(name='boxer', block='crane_boxer', src='[input=east,output=west]', merge=None, index=1, state='[input=east,output=west]',
         text='boxer: entry 1 (orientation) pastes input east, output west', source='TileEntityCraneBase.java:140-176'),
    dict(name='extractor', block='crane_extractor', merge='{Items:[{Slot:0b,id:"minecraft:iron_ingot",count:1}]}', index=0,
         keys=['Items[{Slot:0b}].id'], text='extractor: entry 0 pastes the filter (iron ingot in slot 0)', source='TileEntityCraneBase.java:113-176'),
    dict(name='grabber', block='crane_grabber', merge='{Items:[{Slot:0b,id:"minecraft:iron_ingot",count:1}]}', index=0,
         keys=['Items[{Slot:0b}].id'], text='grabber: entry 0 pastes the filter (iron ingot in slot 0)', source='TileEntityCraneGrabber.java:255'),
    dict(name='router', block='crane_router', merge='{modes:[I;1,2,3,0,1,2],Items:[{Slot:5b,id:"minecraft:iron_ingot",count:1},'
         '{Slot:6b,id:"minecraft:gold_ingot",count:1}]}', index=1, keys=['modes', 'Items[{Slot:5b}].id', 'Items[{Slot:6b}].id'],
         want={'Items[{Slot:5b}].id': None},
         text='sorter: entry 1 pastes all six modes and the group-1 filters (slots 5-9) except its first slot (slot 6 gold, not slot 5 iron)',
         source='TileEntityCraneRouter.java:172-193 (slot > index*5 and < index*5+5: the first slot of a group is not pasted)'),
    dict(name='fluid_duct', block='fluid_duct_neo', merge='{Type:1}', index=0, keys=['Type'],
         text='universal fluid duct: the fluid type is pasted', source='IFluidCopiable.java:44-60'),
    dict(name='duct_paintable', block='fluid_duct_paintable', merge='{paint:{Name:"minecraft:stone"}}', index=0, keys=['paint.Name'],
         text='paintable fluid duct: only the paint is pasted', source='FluidDuctPaintable.java:210-226'),
    dict(name='cable_paintable', block='red_cable_paintable', merge='{paint:{Name:"minecraft:stone"}}', index=0, keys=['paint.Name'],
         text='paintable red copper cable: the paint is pasted', source='BlockCablePaintable.java:191-207'),
    dict(name='rbmk_auto', block='rbmk_control_auto', merge='{levelLower:10d,levelUpper:90d,heatLower:150d,heatUpper:900d,function:1}', index=0,
         keys=['levelLower', 'levelUpper', 'heatLower', 'heatUpper', 'function'], text='RBMK automatic control rod: the four numbers and the function are pasted',
         source='TileEntityRBMKControlAuto.java:171-188'),
    dict(name='compressor', block='machine_compressor', merge='{"0_type":1,"0_p":2s}', index=0, keys=['"0_type"', '"0_p"'],
         text='compressor: the input fluid and the pressure are pasted with no screen open', source='TileEntityMachineCompressorBase.java:275-302'),
    dict(name='combustion_engine', block='machine_combustion_engine', merge='{setting:12,tank_type:19}', index=0, keys=['setting', 'tank_type'],
         text='combustion engine: the fuel type and the burn setting are pasted with no screen open', source='TileEntityMachineCombustionEngine.java:340-354'),
    dict(name='fraction_tower', block='machine_fraction_tower', merge='{tank0_type:19}', index=0, keys=['tank0_type'],
         text='fractioning tower: the input fluid is pasted', source='TileEntityMachineFractionTower.java:22; IFluidCopiable.java:51-60'),
    dict(name='fluid_tank', block='machine_fluid_tank', merge='{Tank_type:1,Tank_max:256000,Tank:5000}', index=0, keys=['Tank_type'],
         text='fluid tank: the fluid type is pasted', source='TileEntityBarrel.java:244-250'),
]


def expectations():
    E = [('recipe', 'JEI shows the recipe " P ", "PCP", "III": iron plate, analog circuit, polymer plate', 'ToolRecipes.java:124'),
         ('stack', 'the settings tool does not stack', 'ItemSettingsTool (maxStackSize 1)'),
         ('tooltip-empty', 'a new tool shows the three description lines and nothing else', 'ItemSettingsTool.addInformation'),
         ('copy-message', 'sneak-use on a machine copies with the "copied" chat line; the tooltip then names the machine', 'ItemSettingsTool.onItemUse'),
         ('copy-stone', 'sneak-use on stone: no settings tool message, the copied data stays', 'ItemSettingsTool.onItemUse'),
         ('paste-reload', 'electric heater, heat exchanger, battery socket and steel barrel keep the pasted values after leaving and reopening the world, '
          'no screen opened', 'ICopiable paste; NEO save marking')]
    E += [('family-%s' % f['name'], f['text'], f['source']) for f in FAMILIES]
    return [dict(id='settings-tool.' + i, text=t, source=s) for i, t, s in E]


def cmd(ctx, command, **kw):
    return ctx.step('cmd', command=command, **kw)


def nbt(ctx, pos, key):
    r = ctx.step('cmd', command='data get block %d %d %d %s' % (pos[0], pos[1], pos[2], key), wait_ticks=6, allow_error=True)
    text = ' '.join(m['text'] for m in r.get('messages', []))
    m = re.search(r'[:：]\s*(-?\d+)[a-z]?\s*$', text)
    return m.group(1) if m else text[-60:]


def chat_since(ctx, started):
    return [m if isinstance(m, str) else m.get('text', '') for m in ctx.step('chat', count=20, since_ms=started).get('messages', [])]


def place(ctx, block, x, z):
    cmd(ctx, 'item replace entity @s weapon.mainhand with hbmsntm:%s' % block)
    ctx.step('view', pos=[x + 0.5, Y, z + 4.5], look_at=[x + 0.5, Y - 0.5, z + 0.5], fly=False, hide_gui=True)
    ctx.step('use', target=dict(pos=[x, Y - 1, z], face='up'), after=8)
    d = ctx.step('dump', **{'from': [x - 3, Y, z - 3], 'to': [x + 3, Y + 3, z + 3]})
    cells = {tuple(int(c) for c in b['pos']): b['props'].get('type', 'core') for b in d['blocks'] if b['block'] == 'hbmsntm:' + block}
    core = next((p for p, t in cells.items() if t == 'core'), None)
    near = max(cells, key=lambda p: (p[2], -abs(p[0] - x), -p[1])) if cells else None  # the cell nearest the player, low
    return core, near


def click(ctx, cell, sneak):
    ctx.step('view', pos=[cell[0] + 0.5, Y, cell[2] + 3.5], look_at=[cell[0] + 0.5, cell[1] + 0.5, cell[2] + 1.0], fly=False, hide_gui=True)
    if sneak:
        ctx.step('key', key='key.keyboard.left.shift', action='press', after=3)
    ctx.step('use', target=dict(pos=list(cell), face='south'), any_hit=True, after=6)
    if sneak:
        ctx.step('key', key='key.keyboard.left.shift', action='release', after=3)


def tooltip(ctx):
    inv = ctx.step('inv')
    return ctx.step('itemtip', slot=inv.get('selected', 0))['tooltip']


def run(ctx):
    t = T[ctx.capture['lang']]
    _lib.setup_world(ctx, freeze=False)
    look = ctx.step('jei', action='lookup', item='hbmsntm:settings_tool', role='output')
    rec = [r for r in look.get('crafting', []) if r['result'].get('item') == 'hbmsntm:settings_tool']
    shape = [sorted(set(a)) for a in rec[0]['ingredients']] if rec else None
    P, C, I = ['hbmsntm:plate_iron'], ['hbmsntm:circuit_analog_board'], ['hbmsntm:plate_polymer']
    want = [[], P, [], P, C, P, I, I, I]
    ctx.check('settings-tool.recipe', len(rec) == 1 and shape == want, 'crafting recipes %d; slots %s' % (len(rec), shape))
    cmd(ctx, 'clear @s', allow_error=True)
    cmd(ctx, 'give @s hbmsntm:settings_tool 2')
    inv = ctx.step('inv')
    tools = [s.get('count') for s in inv['slots'] if s.get('item') == 'hbmsntm:settings_tool']
    ctx.check('settings-tool.stack', tools == [1, 1], 'settings tool stacks in the inventory %s' % tools)
    cmd(ctx, 'clear @s', allow_error=True)
    cmd(ctx, 'item replace entity @s hotbar.0 with hbmsntm:settings_tool')
    ctx.step('key', key='key.keyboard.1', action='tap', after=2)
    tip = tooltip(ctx)
    ctx.check('settings-tool.tooltip-empty', len(tip) == 4 and all(any(d in l for l in tip) for d in t['desc']), 'tooltip (name and lines) %s' % tip)
    ctx.step('view', pos=[OX + 20.5, Y + 6, 4.5], pitch=60.0, yaw=180.0, fly=True, hide_gui=True)
    ctx.step('wait', ticks=60)
    # the machines of the scenario before may reach into this area of the shared world
    cmd(ctx, 'fill %d %d -6 %d %d 10 minecraft:air' % (OX - 6, Y, OX + 45, Y + 6), allow_error=True)
    results = {}
    for i, (block, merge, keys) in enumerate(MACHINES):
        x = OX + 10 * i
        src_core, src_cell = place(ctx, block, x, 0)
        dst_core, dst_cell = place(ctx, block, x + 5, 0)
        if src_core is None or dst_core is None:
            results[block] = ('not placed', src_core, dst_core)
            continue
        cmd(ctx, 'data merge block %d %d %d %s' % (src_core + (merge,)))
        want = {k: nbt(ctx, src_core, k) for k in keys}
        before = {k: nbt(ctx, dst_core, k) for k in keys}
        cmd(ctx, 'item replace entity @s weapon.mainhand with hbmsntm:settings_tool')
        started = ctx.step('wait', ticks=1)['started_ms']
        click(ctx, src_cell, True)
        copied = chat_since(ctx, started)
        if i == 0:
            tip = tooltip(ctx)
            ok = any(t['copied'] in m for m in copied) and len(tip) > 4
            ctx.check('settings-tool.copy-message', ok, 'chat %s; tooltip after copying %s' % (copied, tip))
        click(ctx, dst_cell, False)
        results[block] = (want, dst_core, before)
    # a block without settings: the tool passes, the copied data (from the last machine) stays
    before_tip = tooltip(ctx)
    cmd(ctx, 'setblock %d %d 8 minecraft:stone' % (OX, Y))
    started = ctx.step('wait', ticks=1)['started_ms']
    click(ctx, (OX, Y, 8), True)
    msgs = [m for m in chat_since(ctx, started) if t['copied'] in m or t['failed'] in m]
    tip = tooltip(ctx)
    ctx.check('settings-tool.copy-stone', not msgs and tip == before_tip and len(tip) > 4, 'settings tool chat lines %s; tooltip before %s, after %s' % (msgs, before_tip, tip))
    ctx.step('leave')
    ctx.step('openworld', world=ctx.run.args.world)
    ctx.step('wait', ticks=60)
    ctx.step('view', pos=[OX + 20.5, Y + 6, 4.5], pitch=60.0, yaw=180.0, fly=True, hide_gui=True)
    ctx.step('wait', ticks=40)
    got, ok = {}, True
    for block, r in results.items():
        if r[0] == 'not placed':
            got[block] = r
            ok = False
            continue
        want, dst, before = r
        have = {k: nbt(ctx, dst, k) for k in want}
        got[block] = dict(source=want, target_before=before, target_after_reload=have)
        # a paste that changed nothing cannot pass: the source values must differ from the target's before the paste
        ok = ok and have == want and before != want
    ctx.check('settings-tool.paste-reload', ok, 'per machine %s' % got)
    families(ctx, t)


def raw(ctx, pos, key):
    r = ctx.step('cmd', command='data get block %d %d %d %s' % (pos[0], pos[1], pos[2], key), wait_ticks=6, allow_error=True)
    text = ' '.join(m['text'] for m in r.get('messages', []))
    m = re.search(r'(?:has the following block data|拥有以下方块数据)[:：]\s*(.*)$', text)
    return m.group(1).strip() if m else None


def has_state(ctx, pos, state):
    r = ctx.step('cmd', command='execute if block %d %d %d %s' % (pos + (state,)), wait_ticks=4, allow_error=True)
    return any('passed' in m['text'] or '通过' in m['text'] for m in r.get('messages', []))


def copy_index(ctx):
    r = ctx.step('cmd', command='data get entity @s SelectedItem.components."minecraft:custom_data".copyIndex', wait_ticks=4, allow_error=True)
    m = re.search(r'[:：]\s*(-?\d+)\s*$', ' '.join(x['text'] for x in r.get('messages', [])))
    return int(m.group(1)) if m else None


def families(ctx, t):
    z = 20
    ctx.step('view', pos=[OX + 30.5, Y + 8, z + 6.5], pitch=60.0, yaw=180.0, fly=True, hide_gui=True)
    ctx.step('wait', ticks=40)
    cmd(ctx, 'fill %d %d %d %d %d %d minecraft:air' % (OX - 6, Y, z - 6, OX + 6 * len(FAMILIES) + 6, Y + 8, z + 6), allow_error=True)
    for i, f in enumerate(FAMILIES):
        src, dst = (OX + 6 * i, Y, z), (OX + 6 * i + 3, Y, z)
        cmd(ctx, 'setblock %d %d %d hbmsntm:%s%s' % (src + (f['block'], f.get('src', ''))))
        cmd(ctx, 'setblock %d %d %d hbmsntm:%s' % (dst + (f['block'],)))
        if f.get('merge'):
            cmd(ctx, 'data merge block %d %d %d %s' % (src + (f['merge'],)))
        _lib.placed(ctx)
        if 'state' in f:
            want, before = True, has_state(ctx, dst, 'hbmsntm:' + f['block'] + f['state'])
        else:
            want = {k: raw(ctx, src, k) for k in f['keys']}
            want.update(f.get('want', {}))
            before = {k: raw(ctx, dst, k) for k in f['keys']}
        cmd(ctx, 'item replace entity @s weapon.mainhand with hbmsntm:settings_tool')
        started = ctx.step('wait', ticks=1)['started_ms']
        click(ctx, src, True)
        copied = [m for m in chat_since(ctx, started) if t['copied'] in m]
        index = 0
        if f['index'] == 1:
            # the Alt cycle steps once per 5 ticks after the copy (ItemSettingsTool.onUpdate)
            ctx.step('wait', ticks=10)
            ctx.step('key', key='key.keyboard.left.alt', action='press', after=3)
            ctx.step('key', key='key.keyboard.left.alt', action='release', after=3)
            index = copy_index(ctx)
        click(ctx, dst, False)
        _lib.placed(ctx, ticks=6)
        if 'state' in f:
            after = has_state(ctx, dst, 'hbmsntm:' + f['block'] + f['state'])
            ok = len(copied) == 1 and index == f['index'] and after and not before
            detail = 'copy lines %d; entry %s; target %s before %s, after %s' % (len(copied), index, f['state'], before, after)
        else:
            after = {k: raw(ctx, dst, k) for k in f['keys']}
            ok = len(copied) == 1 and index == f['index'] and after == want and before != want
            detail = 'copy lines %d; entry %s; source %s; target before %s, after %s' % (len(copied), index, want, before, after)
        ctx.check('settings-tool.family-%s' % f['name'], ok, detail)
