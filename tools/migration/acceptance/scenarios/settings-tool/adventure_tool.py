"""Settings tool in adventure mode: the tool takes the click, no screen opens, the copy message comes once.

Expected values follow the 1.7.10 original (cd0cff450): ItemSettingsTool.onItemUseFirst (ItemSettingsTool.java:80-122) runs before
the block's own right-click for every player and returns !world.isRemote, so a click with the tool never opens the machine's
screen; a sneaking click copies and prints one "copied settings" line (:101-105), a plain click pastes (:117-119). NEO has to hand
that click to the tool by event for a player who may not build (CommonEvents.java:115-135, SettingsToolItem.onItemUseFirst), so the
check is that the sorter's screen stays closed for the tool, the copy line is printed once (not twice by the event and NeoForge's own
onItemUseFirst call), and that the same adventure player with an empty hand does open the screen (so a missed click cannot pass as
"no screen"). What an adventure paste does to the target is a NEO rule (the paste checks that the player may build), not the original's,
and is recorded without a verdict.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _lib  # noqa: E402

SCENARIO = dict(
    id='settings-tool.adventure_tool',
    feature='settings-tool',
    title='Settings tool in adventure mode: right-click on a sorter opens no screen and copies once',
    group='solo',
    capture=dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70, hide_gui=False),
)

Y = -60
OX = 1700
FORMAT_ERROR = 'Format error: '
COPIED = 'item.hbmsntm.settings_tool.copied'
SRC_MODES = [1, 2, 3, 0, 1, 2]


def expectations():
    E = [('adventure-copy-once', 'adventure mode: a sneaking right-click on a sorter with the settings tool opens no screen, prints the "copied" line exactly once '
          'and leaves the sorter\'s modes in the tool', 'ItemSettingsTool.java:80-122 (original); CommonEvents.java:115-135, SettingsToolItem.java (NEO)'),
         ('adventure-paste-no-screen', 'adventure mode: a plain right-click on another sorter with the copied tool opens no screen and prints no further "copied" line',
          'ItemSettingsTool.java:117-119, :121 (return !world.isRemote)'),
         ('adventure-empty-hand-opens', 'control: the same adventure player\'s empty-hand right-click on the sorter does open its screen',
          'BlockCraneRouter right-click (screen); Goal 32 adventure rule: only the tool takes the click')]
    return [dict(id='settings-tool.' + i, text=t, source=s) for i, t, s in E]


def cmd(ctx, command, **kw):
    return ctx.step('cmd', command=command, **kw)


def chat_lines(ctx, started):
    return [m if isinstance(m, str) else m.get('text', '') for m in ctx.step('chat', count=30, since_ms=started).get('messages', [])]


def click(ctx, pos, sneak):
    """One right-click from two blocks south of the block; returns (the hit block pos or None, the screen class open afterwards, lines
    chat received during it). A screen is closed again."""
    ctx.step('view', pos=[pos[0] + 0.5, Y, pos[2] + 2.5], look_at=[pos[0] + 0.5, pos[1] + 0.5, pos[2] + 0.5], fly=False, hide_gui=False)
    started = ctx.step('wait', ticks=1)['started_ms']
    if sneak:
        _lib.sneak(ctx, True)
    try:
        hit = ctx.step('use', target=dict(pos=list(pos), face='south'), any_hit=True, after=6).get('hit') or {}
    finally:
        if sneak:
            _lib.sneak(ctx, False)
    screen = ctx.step('hud', frames=2).get('screen')
    if screen:
        ctx.step('close')
    on_target = hit.get('type') == 'BLOCK' and [int(v) for v in hit.get('pos', [])] == list(pos)
    return (list(pos) if on_target else None), screen, chat_lines(ctx, started)


def modes_of(ctx, pos):
    r = ctx.server('data get block %d %d %d modes' % tuple(pos), allow_error=True)
    return ' '.join(m for m in r['messages'] if m.strip())[-40:]


def run(ctx):
    _lib.setup_world(ctx, freeze=False)
    _lib.go_near(ctx, OX + 2, Y, 0)
    cmd(ctx, 'clear @s', allow_error=True)
    template = ctx.step('i18n', keys=[COPIED])['texts'][COPIED] or ''
    template = template[len(FORMAT_ERROR):] if template.startswith(FORMAT_ERROR) else template     # the client's answer for a template with a placeholder and no argument
    head, _, tail = template.partition('%s')
    src, dst = (OX, Y, 0), (OX + 4, Y, 0)
    cmd(ctx, 'setblock %d %d %d hbmsntm:crane_router' % src)
    cmd(ctx, 'setblock %d %d %d hbmsntm:crane_router' % dst)
    cmd(ctx, 'data merge block %d %d %d {modes:[I;%s]}' % (src + (','.join(str(m) for m in SRC_MODES),)))
    cmd(ctx, 'item replace block %d %d %d container.1 with minecraft:iron_ingot' % src)
    cmd(ctx, 'data merge block %d %d %d {modes:[I;3,3,3,3,3,3]}' % dst)
    cmd(ctx, 'gamemode adventure')
    _lib.placed(ctx)
    cmd(ctx, 'item replace entity @s weapon.mainhand with hbmsntm:settings_tool')
    ctx.step('wait', ticks=4)
    hit, screen, lines = click(ctx, src, True)
    copied = [l for l in lines if head and head in l and l.endswith(tail)]
    held = ctx.server('data get entity @p SelectedItem.components', allow_error=True)
    held_text = ' '.join(held['messages'])
    in_tool = re.search(r'modes:\s*\[I;\s*%s\]' % r',\s*'.join(str(m) for m in SRC_MODES), held_text) is not None
    ctx.check('settings-tool.adventure-copy-once', hit is not None and not screen and len(copied) == 1 and in_tool,
              'hit the sorter %s; screen after the click %s; copied lines %d %s (the line is "%s" with the machine name); the tool holds the sorter\'s modes %s'
              % (hit is not None, screen, len(copied), copied, template, in_tool))
    before = modes_of(ctx, dst)
    hit, screen, lines = click(ctx, dst, False)
    again = [l for l in lines if head and head in l and l.endswith(tail)]
    ctx.check('settings-tool.adventure-paste-no-screen', hit is not None and not screen and not again,
              'hit the second sorter %s; screen after the click %s; copied lines %d; its modes before %s, after %s (what an adventure paste does '
              'to them is a NEO rule, not checked)' % (hit is not None, screen, len(again), before, modes_of(ctx, dst)))
    cmd(ctx, 'item replace entity @s weapon.mainhand with minecraft:air')
    ctx.step('wait', ticks=4)
    hit, screen, _ = click(ctx, dst, False)
    ctx.check('settings-tool.adventure-empty-hand-opens', hit is not None and bool(screen) and 'router' in screen.lower(),
              'hit the second sorter %s; screen after an empty-hand click: %s' % (hit is not None, screen))
    cmd(ctx, 'gamemode creative')
