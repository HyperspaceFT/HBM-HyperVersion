"""Player-facing messages that came from literals in the 1.7.10 original and are language keys in NEO, read in Chinese.

The original wrote these texts as English literals (HbmPlayerProps.java:102-125 jetpack, magnet and HUD toggle messages,
ItemMultiDetonator.java:56,76,112,127 detonator, ItemModCharm.java:23-32 charms, ItemKeyPin.java:18-25 keys, BlockWriting.java:26-35
the concrete inscription, DamageResistanceHandler.java damage categories); NEO translates them. Each trigger runs through real use
where the executor reaches it: the toggle keys C, Z and V (HbmKeybinds.java:27-29) answer with an on-screen line (read with the hud
step), the detonator and the marked brick answer in chat, charms and keys are tooltips. The expected Chinese text is what the client's
own language step returns for the key; a line must hold it, hold no translation key, and the expected text must itself contain Chinese
(a key missing from zh_cn would fall back to English and fail that). The damage-resistance categories only appear in item tooltips
that the armor configuration (hbmArmor.json) gives resistances, which the default configuration does not, so only their strings are read.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _lib  # noqa: E402

SCENARIO = dict(
    id='localization-zh-cn.zh_messages',
    feature='localization-zh-cn',
    title='Messages that became language keys read in Chinese: toggles, detonator, charms, keys, concrete inscription, damage categories',
    group='solo',
    capture=dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70, hide_gui=False),
)

Y = -60
OX = 2000
FORMAT_ERROR = 'Format error: '
KEY = re.compile(r'(?<![\w.])(?:[a-z][a-z0-9_]*\.)+[a-z0-9_]+(?![\w.])')
NAMESPACE_KEY = re.compile(r'(?:item|block|tile|desc|container|gui|info|hbmsntm|trait|tooltip|damage|death)\.')
TOGGLES = [('jetpack', 'key.keyboard.c', 'info.jetpack_on', 'info.jetpack_off'), ('magnet', 'key.keyboard.z', 'info.magnet_on', 'info.magnet_off'),
           ('hud', 'key.keyboard.v', 'info.hud_on', 'info.hud_off')]
DET = 'item.hbmsntm.obj_detonator.'
MARKED = ['block.hbmsntm.brick_concrete_marked.msg%d' % i for i in range(10)]
CHARMS = [('meteor_charm', ['item.hbmsntm.obj_mod_charm.blessed', 'item.hbmsntm.meteor_charm.desc1', 'item.hbmsntm.meteor_charm.desc2']),
          ('protection_charm', ['item.hbmsntm.obj_mod_charm.blessed', 'item.hbmsntm.protection_charm.desc1', 'item.hbmsntm.protection_charm.desc2',
                                'item.hbmsntm.protection_charm.desc3'])]
CATEGORIES = ['damage.category.ENERGY', 'damage.category.EXPLOSION', 'damage.category.FIRE', 'damage.category.PHYSICAL', 'damage.other', 'damage.item',
              'damage.inset']


def expectations():
    E = [('zh-message-jetpack', 'the C key toggles the jetpack and the on-screen line is Chinese, on then off', 'HbmPlayerProps.java:102-125 (original); HbmPlayerAttachments.java:80-91'),
         ('zh-message-magnet', 'the Z key toggles the magnet and the on-screen line is Chinese, on then off', 'HbmPlayerProps.java:102-125; HbmPlayerAttachments.java:93-104'),
         ('zh-message-hud', 'the V key toggles the HUD and the on-screen line is Chinese, on then off', 'HbmPlayerProps.java:102-125; HbmPlayerAttachments.java:106-117'),
         ('zh-message-detonator', 'the multi detonator answers in Chinese: no position set, position added, triggered 0/1, positions cleared',
          'ItemMultiDetonator.java:56,76,112,127; MultiDetonatorItem.java:37-97'),
         ('zh-tooltip-charm', 'the meteor charm and the protection charm tooltips are Chinese', 'ItemModCharm.java:23-32; ModCharmItem.java:22-33'),
         ('zh-tooltip-key', 'the key and the counterfeit key tooltips are Chinese: unset, configuration with pins, fixed', 'ItemKeyPin.java:18-25; KeyPinItem.java:19-32'),
         ('zh-message-inscription', 'the marked concrete brick prints its ten inscription lines in Chinese', 'BlockWriting.java:26-35; WritingBlock.java:17-31'),
         ('zh-damage-categories', 'the damage-resistance category and heading strings are Chinese (strings only: the default armor configuration shows none in a tooltip)',
          'DamageResistanceHandler.java (original and NEO addInfo)')]
    return [dict(id='localization-zh-cn.' + i, text=t, source=s) for i, t, s in E]


def cmd(ctx, command, **kw):
    return ctx.step('cmd', command=command, **kw)


def has_cjk(text):
    return any('一' <= ch <= '鿿' for ch in text or '')


def zh(ctx, keys):
    return ctx.step('i18n', keys=list(keys))['texts']


def fill(template, *args):
    """A translation with its %s / %1$s placeholders replaced by `args`; the i18n step reads a template with placeholders without arguments,
    which the client answers as "Format error: <template>", and that prefix is dropped."""
    out = template[len(FORMAT_ERROR):] if template.startswith(FORMAT_ERROR) else template
    for i, a in enumerate(args, 1):
        out = out.replace('%%%d$s' % i, str(a))
    for a in args:
        out = out.replace('%s', str(a), 1)
    return out


def raw_keys(lines):
    return [k for line in lines for k in KEY.findall(line) if NAMESPACE_KEY.match(k)]


def chat_since(ctx, started):
    return [m if isinstance(m, str) else m.get('text', '') for m in ctx.step('chat', count=30, since_ms=started).get('messages', [])]


def toggle(ctx, name, key, on, off):
    texts = zh(ctx, [on, off])
    cjk = has_cjk(texts[on]) and has_cjk(texts[off])
    seen = []
    for _ in range(2):
        ctx.step('key', key=key, action='tap', hold=3, after=2)
        lines = [t['text'] for t in ctx.step('hud', frames=40)['texts']]
        seen.append(lines)
        ctx.step('wait', ticks=40)
    shown = [next((k for k in (on, off) if texts[k] and any(texts[k] in l for l in lines)), None) for lines in seen]
    raw = raw_keys([l for lines in seen for l in lines])
    ok = cjk and sorted(s or '' for s in shown) == sorted([on, off]) and not raw
    ctx.check('localization-zh-cn.zh-message-' + name, ok,
              'key %s pressed twice; expected texts "%s" / "%s" (Chinese: %s); shown the first time %s, the second time %s; screen lines %s; translation keys on screen %s'
              % (key, texts[on], texts[off], cjk, shown[0], shown[1], seen, raw))


def detonator(ctx):
    keys = [DET + n for n in ('pos_none', 'pos_added', 'triggered', 'pos_cleared')]
    t = zh(ctx, keys)
    want = [t[keys[0]], t[keys[1]], fill(t[keys[2]] or '', 0, 1), t[keys[3]]]
    stone = (OX + 8, Y, 0)
    cmd(ctx, 'setblock %d %d %d minecraft:stone' % stone)
    cmd(ctx, 'item replace entity @s weapon.mainhand with hbmsntm:detonator_multi')
    ctx.step('wait', ticks=4)
    got = []

    def read(action):
        started = ctx.step('wait', ticks=1)['started_ms']
        action()
        ctx.step('wait', ticks=6)
        got.append(chat_since(ctx, started))

    def sky(sneak):
        ctx.step('view', pos=[OX + 0.5, Y, 4.5], pitch=-90.0, yaw=0.0, fly=False, hide_gui=False)
        if sneak:
            _lib.sneak(ctx, True)
        try:
            ctx.step('use', after=6)
        finally:
            if sneak:
                _lib.sneak(ctx, False)

    read(lambda: sky(False))                                                       # nothing set yet
    read(lambda: _lib.use_on(ctx, stone, 'south', [stone[0] + 0.5, Y, 2.5], crouch=True))   # sneaking on a block adds its position
    read(lambda: sky(False))                                                       # plain use triggers the one position: a stone block is no bomb
    read(lambda: sky(True))                                                        # sneaking use clears
    found = [next((l for l in lines if l.endswith(w) and l.startswith('[')), None) for lines, w in zip(got, want)]
    raw = raw_keys([l for lines in got for l in lines])
    ctx.check('localization-zh-cn.zh-message-detonator', all(found) and all(has_cjk(w) for w in want) and not raw,
              'expected endings %s; chat line found per step %s; chat per step %s; translation keys in chat %s' % (want, found, got, raw))


def tooltips(ctx):
    ctx.step('mod', shift=False)
    texts = zh(ctx, [k for _, keys in CHARMS for k in keys] + ['item.hbmsntm.obj_key_pin.not_set', 'item.hbmsntm.obj_key_pin.configuration',
                                                               'item.hbmsntm.obj_key_pin.fixed'])
    seen, bad = {}, []
    for item, keys in CHARMS:
        tip = ctx.step('itemtip', item='hbmsntm:' + item)['tooltip']
        seen[item] = tip
        bad += [k for k in keys if not texts[k] or not has_cjk(texts[k]) or texts[k] not in tip]
    ctx.check('localization-zh-cn.zh-tooltip-charm', not bad and not raw_keys([l for t in seen.values() for l in t]),
              'tooltips %s; expected lines missing or not Chinese: %s' % (seen, bad))
    unset, fixed = 'item.hbmsntm.obj_key_pin.not_set', 'item.hbmsntm.obj_key_pin.fixed'
    conf = fill(texts['item.hbmsntm.obj_key_pin.configuration'] or '', 5)
    key_unset = ctx.step('itemtip', item='hbmsntm:key')['tooltip']
    key_set = ctx.step('itemtip', item='hbmsntm:key[minecraft:custom_data={pins:5}]', allow_fail=True)
    fake = ctx.step('itemtip', item='hbmsntm:key_fake')['tooltip']
    set_tip = key_set.get('tooltip', []) if key_set.get('status') == 'ok' else []
    ok = (all(has_cjk(texts[k]) for k in (unset, fixed, 'item.hbmsntm.obj_key_pin.configuration')) and texts[unset] in key_unset and texts[fixed] not in key_unset
          and conf in set_tip and texts[unset] in fake and texts[fixed] in fake
          and not raw_keys(key_unset + set_tip + fake))
    ctx.check('localization-zh-cn.zh-tooltip-key', ok, 'key with no pins %s; key with 5 pins %s (expected line "%s"; step %s); counterfeit key %s; expected "%s" and "%s"'
              % (key_unset, set_tip, conf, key_set.get('status'), fake, texts[unset], texts[fixed]))


def inscription(ctx):
    t = zh(ctx, MARKED)
    pos = (OX + 12, Y, 0)
    cmd(ctx, 'setblock %d %d %d hbmsntm:brick_concrete_marked' % pos)
    _lib.placed(ctx)
    _lib.empty_hand(ctx)
    started = ctx.step('wait', ticks=1)['started_ms']
    _lib.use_on(ctx, pos, 'south', [pos[0] + 0.5, Y, 2.5])
    ctx.step('wait', ticks=6)
    lines = chat_since(ctx, started)
    want = [t[k] for k in MARKED]
    tail = [l for l in lines if l in want]
    ctx.check('localization-zh-cn.zh-message-inscription', all(want) and all(has_cjk(w) for w in want) and tail == want and not raw_keys(lines),
              'expected %d lines; chat lines equal to them, in order: %d; chat %s' % (len(want), len(tail), lines))


def categories(ctx):
    t = zh(ctx, CATEGORIES)
    bad = [k for k in CATEGORIES if not has_cjk(t[k])]
    ctx.check('localization-zh-cn.zh-damage-categories', not bad, 'strings %s; not Chinese: %s' % (t, bad))


def run(ctx):
    if ctx.capture['lang'] != 'zh_cn':
        for e in expectations():
            ctx.not_run(e['id'], 'the run language is %s, not zh_cn' % ctx.capture['lang'])
        return
    _lib.setup_world(ctx, freeze=False)
    cmd(ctx, 'clear @s', allow_error=True)
    ctx.step('view', pos=[OX + 0.5, Y, 4.5], pitch=0.0, yaw=0.0, fly=False, hide_gui=False)
    ctx.step('wait', ticks=40)
    for name, key, on, off in TOGGLES:
        toggle(ctx, name, key, on, off)
    detonator(ctx)
    tooltips(ctx)
    inscription(ctx)
    categories(ctx)
