"""A kill with a sedna-family weapon gives a death message that names the shooter, read in Chinese.

Expected values follow the 1.7.10 original (cd0cff450): a bullet's damage source with a shooter is DamageSourceSednaWithAttacker
(BulletConfig.java:157), whose func_151519_b (DamageSourceSednaWithAttacker.java:25-30) returns "death.sedna.<class>.attacker" with the
victim's and the shooter's names; for the physical class the English text is "%1$s was shot by %2$s." (en_US.lang:968) and the Chinese
"%1$s 被 %2$s 射杀了" (zh_CN.lang:785). Without a shooter it is the plain "%1$s was shot." with no shooter (DamageSourceSednaNoAttacker).
NEO builds the source with the shooter (BulletConfig.java:185-201), so the line is the ".player" key of the same text.

Death messages of mobs are not broadcast, except that a tamed animal tells its owner (TamableAnimal.die sends its combat tracker's
death message when the game rule showDeathMessages is on). So the victim is a tamed, named, sitting cat owned by the player, shot with
the debug gun (reloaded with the R key from debug ammo, fired through the attack binding, as a player does) and the owner's chat is read.
A shot that did not name the shooter (the plain key) or a melee kill ("slain by") would not equal the expected line.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _lib  # noqa: E402

SCENARIO = dict(
    id='localization-zh-cn.death_message',
    feature='localization-zh-cn',
    title='Death message of a mob killed with a sedna weapon names the shooter (Chinese)',
    group='solo',
    capture=dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70, hide_gui=False),
)

Y = -60
X, CAT_Z = 2200, -4
KEY = 'death.attack.sednaPhysical.player'
NAME = 'Mog'
FORMAT_ERROR = 'Format error: '


def expectations():
    E = [('death-message-weapon', 'a tamed cat killed with the debug gun by its owner: the owner\'s chat holds the sentence "<cat> was shot by <owner>" in Chinese, '
          'with the shooter\'s name',
          'DamageSourceSednaWithAttacker.java:12-31, BulletConfig.java:157, en_US.lang:968, zh_CN.lang:785 (original); BulletConfig.java:185-201 (NEO)')]
    return [dict(id='localization-zh-cn.' + i, text=t, source=s) for i, t, s in E]


def cmd(ctx, command, **kw):
    return ctx.step('cmd', command=command, **kw)


def last_value(ctx, command):
    r = ctx.server(command)
    lines = [m for m in r['messages'] if m.strip()]
    return _lib.data_value(lines[-1]) if lines else None


def player_name(ctx):
    """The player's name from the server's `list` reply (the text after its last colon)."""
    lines = [m for m in ctx.server('list')['messages'] if m.strip()]
    return re.split(r'[:：]\s*', lines[-1])[-1].strip() if lines else ''


def has_cjk(text):
    return any('\u4e00' <= ch <= '\u9fff' for ch in text)


def fill(template, victim, shooter):
    return template.replace('%1$s', victim).replace('%2$s', shooter)


def cats(ctx):
    d = ctx.step('dump', **{'from': [X - 3, Y - 1, CAT_Z - 3], 'to': [X + 3, Y + 2, 2]}, entities=True)
    return [e for e in d.get('entities', []) if e['type'] == 'minecraft:cat']


def run(ctx):
    _lib.setup_world(ctx, freeze=False)
    cmd(ctx, 'gamerule showDeathMessages true')
    _lib.go_near(ctx, X, Y, 0)
    cmd(ctx, 'clear @s', allow_error=True)
    uuid = last_value(ctx, 'data get entity @p UUID')
    who = player_name(ctx)
    template = ctx.step('i18n', keys=[KEY])['texts'][KEY] or ''
    template = template[len(FORMAT_ERROR):] if template.startswith(FORMAT_ERROR) else template     # the client's answer for a template with placeholders and no arguments
    want = fill(template, NAME, who)
    if isinstance(uuid, list) and len(uuid) == 4:
        cmd(ctx, 'summon minecraft:cat %d.5 %d %d.5 {Owner:[I;%s],Sitting:1b,NoAI:1b,PersistenceRequired:1b,CustomName:\'"%s"\'}'
            % (X, Y, CAT_Z, ','.join(str(int(v)) for v in uuid), NAME))
    ctx.step('wait', ticks=10)
    before = len(cats(ctx))
    cmd(ctx, 'gamemode survival')
    cmd(ctx, 'give @s hbmsntm:gun_debug')
    cmd(ctx, 'give @s hbmsntm:ammo_debug 24')
    _lib.hold(ctx, 'hbmsntm:gun_debug')
    ctx.step('view', pos=[X + 0.5, Y, 0.5], look_at=[X + 0.5, Y + 0.35, CAT_Z + 0.5], fly=False, hide_gui=False)
    ctx.step('wait', ticks=40)
    ctx.step('key', key='key.keyboard.r', action='tap', hold=3, after=2)
    ctx.step('wait', ticks=100)
    started = ctx.step('wait', ticks=1)['started_ms']
    remaining = before
    for _ in range(4):
        ctx.step('attack', hold=10, after=4)
        ctx.step('wait', ticks=60)
        remaining = len(cats(ctx))
        if remaining == 0:
            break
    ctx.step('wait', ticks=20)
    lines = [m if isinstance(m, str) else m.get('text', '') for m in ctx.step('chat', count=40, since_ms=started).get('messages', [])]
    ctx.check('localization-zh-cn.death-message-weapon',
              before == 1 and remaining == 0 and bool(who) and bool(template) and has_cjk(template) and want in lines,
              'the player is "%s" (uuid %s); cats before %d, after %d; expected chat line "%s" (from "%s"); chat lines mentioning the cat %s'
              % (who, uuid, before, remaining, want, template, [l for l in lines if NAME in l]))
    cmd(ctx, 'kill @e[type=minecraft:cat]', allow_error=True)
    cmd(ctx, 'gamemode creative')

