"""Language scan, layer 1: every item's name and tooltip lines in Chinese and in English, as the client builds them.

Reads the seven hbmsntm creative tabs (every stack they show, variants included) and every registered hbmsntm item as its
default stack, once normally and once with Shift held (many descriptions appear only then), in zh_cn and in en_us. A
line that is a translation key (lower-case dotted words such as item.hbmsntm.foo or desc.x.y) or that still holds a
format placeholder (%s, %d, %1$s) is a leak, and so is a tooltip that throws (the executor reports it as one line). In Chinese, a name identical to the English name is listed for a person
(proper nouns and symbols are legitimately the same). The complete findings go to <run>/language-scan-items.json.
"""
import json
import re

SCENARIO = dict(
    id='localization-zh-cn.items',
    feature='localization-zh-cn',
    title='Language scan 1: names and tooltip lines of every item in Chinese and English',
    group='solo',
    capture=dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70),
)

TABS = ('parts', 'control', 'blocks', 'machine', 'nuke', 'missile', 'consumable')
KEY = re.compile(r'(?<![\w.])(?:[a-z][a-z0-9_]*\.)+[a-z0-9_]+(?![\w.])')
PLACEHOLDER = re.compile(r'%(?:\d+\$)?[sdf]')
NAMESPACE_KEY = re.compile(r'(?:item|block|tile|desc|container|gui|info|hbmsntm|trait|tooltip)\.')


def expectations():
    E = [
        ('items-zh-keys', 'Chinese: no item name or tooltip line is a translation key or holds an unfilled placeholder'),
        ('items-en-keys', 'English: no item name or tooltip line is a translation key or holds an unfilled placeholder'),
        ('items-zh-same-as-en', 'record for a person: Chinese names identical to the English name'),
        ('items-coverage', 'record: stacks and items read per language, normal and with Shift'),
    ]
    return [dict(id='localization-zh-cn.' + i, text=t, source='Screen.getTooltipFromItem') for i, t in E]


def leaks_of(lines):
    out = []
    for line in lines:
        keys = [k for k in KEY.findall(line) if NAMESPACE_KEY.match(k) or k == line.strip()]
        if keys or PLACEHOLDER.search(line) or line.startswith('tooltip error: '):
            out.append(line)
    return out


def read_language(ctx, code):
    ctx.step('lang', code=code)
    found = {}  # (stack, shift) -> lines
    for shift in (False, True):
        ctx.step('mod', shift=shift)
        for tab in TABS:
            r = ctx.step('tab', tab='hbmsntm:' + tab, tooltips=True, timeout_ticks=20 * 60)
            for stack, lines in zip(r['items'], r['tooltips']):
                found[(stack, shift)] = lines
        r = ctx.step('items', namespace='hbmsntm', timeout_ticks=20 * 60)
        for item in r['items']:
            found.setdefault((item['item'], shift), item['tooltip'])
    ctx.step('mod', shift=False)
    return found


def run(ctx):
    report = {}
    names = {}
    try:
        for code in ('zh_cn', 'en_us'):
            found = read_language(ctx, code)
            leaks = {}
            for (stack, shift), lines in sorted(found.items()):
                bad = leaks_of(lines)
                if bad:
                    leaks.setdefault(stack, {})['shift' if shift else 'normal'] = bad
            names[code] = {stack: lines[0] if lines else '' for (stack, shift), lines in found.items() if not shift}
            report[code] = dict(stacks=len({s for s, _ in found}), leaks=leaks)
    finally:
        ctx.step('mod', shift=False)
        ctx.step('lang', code=ctx.capture['lang'])
    same = sorted(s for s, n in names['zh_cn'].items() if n and n == names['en_us'].get(s))
    report['zh_same_as_en'] = same
    (ctx.run.dir / 'language-scan-items.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    for code, eid in (('zh_cn', 'items-zh-keys'), ('en_us', 'items-en-keys')):
        leaks = report[code]['leaks']
        sample = '; '.join('%s: %s' % (s, ' / '.join(v.get('normal', v.get('shift', []))[:2])) for s, v in list(leaks.items())[:8])
        ctx.check('localization-zh-cn.' + eid, not leaks, '%d of %d stacks with a leak%s' % (len(leaks), report[code]['stacks'],
                                                                                              (': ' + sample) if sample else ''),
                  evidence=['language-scan-items.json'])
    ctx.review('localization-zh-cn.items-zh-same-as-en', '%d names: %s' % (len(same), ', '.join(same[:30])), evidence=['language-scan-items.json'])
    ctx.review('localization-zh-cn.items-coverage', 'zh_cn %d stacks, en_us %d stacks (tabs %s and every registered item; normal and Shift)'
               % (report['zh_cn']['stacks'], report['en_us']['stacks'], ', '.join(TABS)))
