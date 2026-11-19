"""JEI pages of the recipe-completion rows: the centrifuge's gravel and the sellafield stones, the fuel crafting recipes, the
laminate's glass slot, the irradiation channel's potato and the burn times of coke and briquettes.

What the executor's jei step can read decides the shape of each row (JeiBridge.java: `lookup` gives the recipe categories with their
recipe counts for an item as input or output, and the crafting recipes with result and ingredient alternatives; `recipes` opens
JEI's recipe screen for an item; the hud step lists the texts the screen draws). So each row is a machine check on the lookup data
where the data decides it, with the picture of the page taken beside it; what only the picture shows (the slot that cycles through
the glasses, the fourth output slot) is a review item with the exact thing to look at.

Expected values follow the 1.7.10 original:
- centrifuge: every ore row ends in gravel (CentrifugeRecipes.java:54-184: twenty rows, each `new ItemStack(Blocks.gravel, 1)` last),
  only nether quartz and nether gold keep netherrack in NEO, and nothing gives stone; diamond and emerald ores and their sellafield
  forms give three powders and gravel (CentrifugeRecipes.java:78-88; the sellafield ores and the diamond gravel are the ores of the
  diamond and emerald dictionary entries, OreDictManager.java:341-342).
- fuel crafting recipes: the LES and lithium zirnox rods (RodRecipes.java:35-36), the neptunium and schrabidium fuel billets
  (MineralRecipes.java:174-175,179-180), the schrabidium fuel, HES and LES ingots from nine nuggets (MineralRecipes.java:416-418) and
  the flat stamps that also take nether bricks (CraftingManager.java:347-356).
- laminate: the chemical plant recipe takes any glass block (ChemicalPlantRecipes.java:369-372, OreDictManager.java:639-644), so its
  glass slot lists every glass and JEI cycles through them; the only chemical plant recipe that takes glass panes is the polarized glass
  (ChemicalPlantRecipes.java:374-377).
- irradiation channel: a potato gives a poisonous potato (OutgasserRecipes.java:54).
- burn times: coke 3,200, coal, lignite and wood briquettes 2,000, 1,600 and 400 ticks (FuelHandler.java:38,49-51); JEI's fuel page
  prints how many items such a fuel smelts, the burn time over the 200 ticks of one smelt.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _lib  # noqa: E402

SCENARIO = dict(
    id='recipe-completion.jei_pages',
    feature='recipe-completion',
    features=['recipe-completion', 'centrifuge', 'chemical-plant', 'rbmk-outgasser', 'basic-carbon-materials'],
    title='JEI pages: centrifuge gravel and sellafield rows, fuel crafting recipes, laminate glass cycle, irradiation potato, burn times',
    group='solo',
    capture=dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70),
)

H = 'hbmsntm:'
CENTRIFUGE = H + 'centrifuge'
CHEMPLANT = H + 'chemical_plant'
IRRADIATION = H + 'irradiation'
TITLE_CENTRIFUGE = 'container.machine_centrifuge'      # CentrifugeRecipeHandler.getTitle
TITLE_CHEMPLANT = 'container.machineChemicalPlant'     # ChemicalPlantRecipeHandler.getTitle
TITLE_OUTGASSER = 'block.hbmsntm.rbmk_outgasser'       # IrradiationRecipeHandler.getTitle (the channel's name)

# CentrifugeRecipes.java:54-184: ores whose row ends in gravel; the uranium and schrabidium rows serve the nether ores as well (:126-130,144-148)
GRAVEL_ORES = ['minecraft:iron_ore', 'minecraft:deepslate_coal_ore', H + 'ore_uranium', H + 'ore_gneiss_iron', H + 'ore_nether_uranium',
               H + 'ore_nether_uranium_scorched', H + 'ore_nether_schrabidium']
GRAVEL_ROWS_MIN = 20          # the original's ore rows ending in gravel, CentrifugeRecipes.java:58-184
NETHERRACK_ROWS_MIN = 2       # nether quartz ore and nether gold ore keep netherrack
SELLAFIELD = [(H + 'ore_sellafield_diamond', H + 'powder_diamond'), (H + 'ore_sellafield_emerald', H + 'powder_emerald'),
              (H + 'gravel_diamond', H + 'powder_diamond')]
# rows whose output is the powder: diamond (diamond ore, sellafield ore, diamond gravel), emerald (emerald ore, sellafield ore)
POWDER_ROWS_MIN = {H + 'powder_diamond': 3, H + 'powder_emerald': 2}

ZIRNOX_LES, ZIRNOX_LITHIUM = 8, 9   # ZirnoxType ordinals, original EnumZirnoxType (ItemZirnoxRod.java:101-112)
ROD = H + 'rod_zirnox'
# (id, result item, count, meta or None, ingredients {item: n}, original line)
FUEL_RECIPES = [
    ('les-rod', ROD, 1, ZIRNOX_LES, {H + 'rod_zirnox_empty': 1, H + 'billet_les': 2}, 'RodRecipes.java:35'),
    ('lithium-rod', ROD, 1, ZIRNOX_LITHIUM, {H + 'rod_zirnox_empty': 1, H + 'lithium': 2}, 'RodRecipes.java:36'),
    ('neptunium-billets', H + 'billet_neptunium_fuel', 3, None, {H + 'billet_u238': 2, H + 'billet_neptunium': 1}, 'MineralRecipes.java:174'),
    ('neptunium-nuggets', H + 'billet_neptunium_fuel', 1, None, {H + 'nugget_neptunium': 2, H + 'nugget_u238': 4}, 'MineralRecipes.java:175'),
    ('schrabidium-billets', H + 'billet_schrabidium_fuel', 3, None,
     {H + 'billet_schrabidium': 1, H + 'billet_neptunium': 1, H + 'billet_beryllium': 1}, 'MineralRecipes.java:179'),
    ('schrabidium-nuggets', H + 'billet_schrabidium_fuel', 1, None,
     {H + 'nugget_schrabidium': 2, H + 'nugget_neptunium': 2, H + 'nugget_beryllium': 2}, 'MineralRecipes.java:180'),
    ('schrabidium-ingot', H + 'ingot_schrabidium_fuel', 1, None,
     {H + 'nugget_schrabidium': 3, H + 'nugget_neptunium': 3, H + 'nugget_beryllium': 3}, 'MineralRecipes.java:416'),
    ('hes-ingot', H + 'ingot_hes', 1, None, {H + 'nugget_schrabidium': 5, H + 'nugget_neptunium': 2, H + 'nugget_beryllium': 2}, 'MineralRecipes.java:417'),
    ('les-ingot', H + 'ingot_les', 1, None, {H + 'nugget_schrabidium': 1, H + 'nugget_neptunium': 4, H + 'nugget_beryllium': 4}, 'MineralRecipes.java:418'),
    ('stamp-steel', H + 'stamp_steel_flat', 1, None, {'minecraft:nether_brick': 3, H + 'ingot_steel': 3}, 'CraftingManager.java:352'),
    ('stamp-titanium', H + 'stamp_titanium_flat', 1, None, {'minecraft:nether_brick': 3, H + 'ingot_titanium': 3}, 'CraftingManager.java:353'),
    ('stamp-obsidian', H + 'stamp_obsidian_flat', 1, None, {'minecraft:nether_brick': 3, 'minecraft:obsidian': 3}, 'CraftingManager.java:354'),
    ('stamp-desh', H + 'stamp_desh_flat', 1, None, {'minecraft:nether_brick': 4, H + 'ingot_desh': 4, H + 'ingot_ferrouranium': 1}, 'CraftingManager.java:355'),
]
# the two pages of the fuel row that are shown: the LES rod and the HES ingot
FUEL_PAGES = [('les-rod', ROD + '[hbmsntm:meta=%d]' % ZIRNOX_LES), ('hes-ingot', H + 'ingot_hes')]

GLASSES = ['minecraft:glass', H + 'glass_boron', H + 'glass_lead']
LAMINATE = H + 'reinforced_laminate'

# FuelHandler.java:38,49-51: burn ticks, single = 200; JEI prints burn / 200 smelts
BURN = [(H + 'coke_coal', 3200), (H + 'coke_lignite', 3200), (H + 'coke_petroleum', 3200),
        (H + 'briquette_coal', 2000), (H + 'briquette_lignite', 1600), (H + 'briquette_wood', 400)]
SMELTS = re.compile(r'(?:Smelts|烧炼)\s*([0-9][0-9.,]*)\s*(?:items|个物品)')
SMELTS_ONE = re.compile(r'(?:Smelts 1 item|烧炼 1 个物品)')


def expectations():
    E = [
        ('centrifuge.jei-gravel-lookup',
         'the centrifuge category lists each of iron ore, deepslate coal ore, uranium ore, gneiss iron ore, nether uranium ore, scorched nether '
         'uranium ore and nether schrabidium ore as an input; at least %d centrifuge recipes have gravel as an output, none has stone, and at '
         'least %d keep netherrack (nether quartz and nether gold); a build that still ends the rows in stone lists stone and no gravel' % (
             GRAVEL_ROWS_MIN, NETHERRACK_ROWS_MIN),
         'original CentrifugeRecipes.java:54-184 (every ore row ends in new ItemStack(Blocks.gravel, 1))'),
        ('centrifuge.jei-gravel-page',
         'the centrifuge page of uranium ore: four output slots in a row, the fourth is gravel',
         'original CentrifugeRecipes.java:144-148 (uranium row, gravel last)'),
        ('recipe-completion.jei-fuel-recipes',
         'JEI lists crafting recipes with the original ingredients and counts for the LES and lithium zirnox rods, the neptunium and schrabidium '
         'fuel billets (from billets and from nuggets), the schrabidium fuel, HES and LES ingots (nine nuggets) and the flat steel, titanium, '
         'obsidian and desh stamps with nether bricks; a recipe that is missing or has other counts is named',
         'original RodRecipes.java:35-36, MineralRecipes.java:174-175,179-180,416-418, CraftingManager.java:347-356'),
        ('recipe-completion.jei-fuel-recipes-page',
         'the JEI crafting page of the LES zirnox rod (empty rod and two LES billets) and of the HES ingot (nine nuggets) draws all its ingredients '
         'and its result without a missing or empty slot',
         'original RodRecipes.java:35, MineralRecipes.java:417'),
        ('chemical-plant.jei-laminate-lookup',
         'a plain glass block, boron glass and lead glass each find the same chemical plant recipes as an input, the recipe that makes the reinforced '
         'laminate is among them, and a glass pane finds exactly one chemical plant recipe, the polarized glass that takes panes, not the laminate (a pane '
         'that also fitted the laminate would find two); a build whose glass slot took only plain glass finds the recipe for one of the three',
         'original ChemicalPlantRecipes.java:369-372,374-377, OreDictManager.java:639-644'),
        ('chemical-plant.jei-laminate-cycle',
         'the chemical plant page of the reinforced laminate: the glass slot (the first of the two item inputs, left) shows a different glass in each '
         'of four pictures 1.5 s apart; it cycles through plain, boron and lead glass and more',
         'original ChemicalPlantRecipes.java:369-372 (any glass block)'),
        ('rbmk-outgasser.jei-potato',
         'the irradiation channel category lists the potato as an input and the poisonous potato as an output, and does not list a carrot',
         'original OutgasserRecipes.java:54 (potato to poisonous potato)'),
        ('rbmk-outgasser.jei-potato-page',
         'the irradiation channel page of the potato: potato in the input slot, poisonous potato in the output slot',
         'original OutgasserRecipes.java:54'),
        ('centrifuge.jei-sellafield-lookup',
         'sellafield diamond ore, sellafield emerald ore and diamond gravel are centrifuge inputs; the diamond powder is the output of at least 3 '
         'centrifuge recipes and the emerald powder of at least 2 (ore and sellafield ore, and the diamond gravel)',
         'original CentrifugeRecipes.java:78-88, OreDictManager.java:341-342'),
        ('centrifuge.jei-sellafield-page',
         'the centrifuge pages of sellafield diamond ore, sellafield emerald ore and diamond gravel: three identical powder outputs (diamond, emerald, '
         'diamond) and gravel in the fourth slot',
         'original CentrifugeRecipes.java:78-88'),
        ('basic-carbon-materials.jei-burn-times',
         'JEI\'s fuel page of each coke prints "smelts 16 items" (3,200 ticks), of the coal, lignite and wood briquette 10, 8 and 2 (2,000, 1,600 and '
         '400 ticks); a build with the old burn times prints other counts or no fuel page',
         'original FuelHandler.java:38,49-51 (single = 200)'),
    ]
    return [dict(id=i, text=t, source=s) for i, t, s in E]


# ---------------------------------------------------------------- reading JEI

def lookup(ctx, item, role):
    return ctx.step('jei', action='lookup', item=item, role=role)


def rows(r, uid):
    """Recipes of category `uid` in a lookup reply."""
    return (r.get('categories') or {}).get(uid, 0)


def texts_of(hud):
    return [t['text'] for t in hud.get('texts', [])]


def translated(ctx, *keys):
    return ctx.step('i18n', keys=list(keys))['texts']


def show_page(ctx, item, role, found, tries):
    """Opens JEI's recipe screen for `item` and pages through the categories (Shift + Page Down, JEI's next category key) until the texts the
    screen draws satisfy `found`. Returns (hud, True) on the page, (hud, False) after `tries` categories without it."""
    ctx.step('jei', action='recipes', item=item, role=role)
    ctx.step('wait', ticks=8)
    hud = None
    for _ in range(max(1, tries) + 1):
        hud = ctx.step('hud', frames=4)
        if 'RecipesGui' in str(hud.get('screen')) and found(texts_of(hud)):
            return hud, True
        ctx.step('mod', shift=True)
        try:
            ctx.step('key', key='key.keyboard.page.down', action='tap', after=4)
        finally:
            ctx.step('mod', shift=False)
        ctx.step('wait', ticks=4)
    return hud, False


def shot(ctx, name):
    return ctx.step('shot', file=ctx.shot_name(name))['image']['file']


def section(ctx, ids, body):
    """Runs one independent part; its undecided expectations become not-run with the reason when it fails."""
    try:
        ctx.step('close', allow_fail=True)
        ctx.step('mod', shift=False, allow_fail=True)
        body()
    except Exception as e:  # noqa: BLE001 - one broken part must not take the next one with it
        result = getattr(e, 'result', None)
        reason = 'step %s (%s) failed: %s' % (result.get('seq'), result.get('op'), result.get('reason')) if isinstance(result, dict) else repr(e)[:300]
        for eid in ids:
            if eid not in ctx.verdicts:
                ctx.not_run(eid, reason)
    finally:
        try:
            ctx.step('close', allow_fail=True)
            ctx.step('mod', shift=False, allow_fail=True)
        except Exception:  # noqa: BLE001
            pass


# ---------------------------------------------------------------- rows

def centrifuge_gravel(ctx):
    ids = ['centrifuge.jei-gravel-lookup', 'centrifuge.jei-gravel-page']

    def body():
        problems = []
        pages = {}
        for ore in GRAVEL_ORES:
            n = rows(lookup(ctx, ore, 'input'), CENTRIFUGE)
            pages[ore.split(':')[1]] = n
            if n < 1:
                problems.append('%s has no centrifuge recipe as an input' % ore)
        gravel = rows(lookup(ctx, 'minecraft:gravel', 'output'), CENTRIFUGE)
        stone = rows(lookup(ctx, 'minecraft:stone', 'output'), CENTRIFUGE)
        netherrack = rows(lookup(ctx, 'minecraft:netherrack', 'output'), CENTRIFUGE)
        if gravel < GRAVEL_ROWS_MIN:
            problems.append('%d centrifuge recipes give gravel, the original has at least %d' % (gravel, GRAVEL_ROWS_MIN))
        if stone:
            problems.append('%d centrifuge recipes still give stone' % stone)
        if netherrack < NETHERRACK_ROWS_MIN:
            problems.append('%d centrifuge recipes give netherrack, expected at least %d' % (netherrack, NETHERRACK_ROWS_MIN))
        ctx.check(ids[0], not problems, '%s; recipes by input %s; with gravel as output %d, stone %d, netherrack %d' % (
            '; '.join(problems) or 'all as expected', pages, gravel, stone, netherrack))

        title = translated(ctx, TITLE_CENTRIFUGE)[TITLE_CENTRIFUGE]
        first = lookup(ctx, H + 'ore_uranium', 'input')
        hud, ok = show_page(ctx, H + 'ore_uranium', 'input', lambda t: any(title in x for x in t), len(first.get('categories') or {}))
        if not ok:
            ctx.not_run(ids[1], 'the centrifuge page (title "%s") did not come up for uranium ore; categories %s, screen %s, texts %s' % (
                title, list((first.get('categories') or {})), hud.get('screen'), texts_of(hud)[:12]))
            return
        ctx.review(ids[1], 'JEI centrifuge page of uranium ore (title "%s"): one uranium ore in the input slot and four output slots to the right of '
                           'it; the fourth, rightmost output slot must be a gravel block; slots one to three hold the row\'s powder and nuggets' % title, [shot(ctx, 'centrifuge-uranium')])
    section(ctx, ids, body)


def fuel_recipes(ctx):
    ids = ['recipe-completion.jei-fuel-recipes', 'recipe-completion.jei-fuel-recipes-page']

    def body():
        problems = []
        seen = {}
        for name, result, count, meta, want, source in FUEL_RECIPES:
            focus = result + ('[hbmsntm:meta=%d]' % meta if meta is not None else '')
            found = lookup(ctx, focus, 'output').get('crafting', [])
            hit = None
            for r in found:
                res = r['result']
                comp = re.search(r'meta=>(\d+)', res.get('components', ''))
                if res['item'] != result or res['count'] != count or (meta is not None and (not comp or int(comp.group(1)) != meta)):
                    continue
                ing = [alts for alts in r['ingredients'] if alts]
                if len(ing) == sum(want.values()) and all(sum(1 for alts in ing if item in alts) == n for item, n in want.items()):
                    hit = r['id']
                    break
            seen[name] = hit
            if hit is None:
                problems.append('%s (%s): none of the %d crafting recipes for %s has %s x %d from %s' % (
                    name, source, len(found), focus, result, count, want))
        ctx.check(ids[0], not problems, '%s; recipes found %s' % ('; '.join(problems) or 'every recipe is listed with the original ingredients', seen))

        pages = []
        for name, focus in FUEL_PAGES:
            ctx.step('jei', action='recipes', item=focus, role='output')
            ctx.step('wait', ticks=8)
            hud = ctx.step('hud', frames=2)
            if 'RecipesGui' not in str(hud.get('screen')):
                raise RuntimeError('JEI recipe screen for %s did not open (screen %s)' % (focus, hud.get('screen')))
            pages.append(shot(ctx, 'fuel-%s' % name))
            ctx.step('close')
        ctx.review(ids[1], 'two JEI crafting pages, the LES zirnox rod (empty rod and two LES billets, shapeless) and the HES ingot (five schrabidium, '
                           'two neptunium, two beryllium nuggets): every ingredient slot shows an item, the result slot shows the rod / the ingot, no '
                           'slot is empty or shows a missing-texture block', pages)
    section(ctx, ids, body)


def laminate(ctx):
    ids = ['chemical-plant.jei-laminate-lookup', 'chemical-plant.jei-laminate-cycle']

    def body():
        made = lookup(ctx, LAMINATE, 'output')
        by_glass = {g: rows(lookup(ctx, g, 'input'), CHEMPLANT) for g in GLASSES}
        pane = rows(lookup(ctx, 'minecraft:glass_pane', 'input'), CHEMPLANT)
        recipe = rows(made, CHEMPLANT)
        same = len(set(by_glass.values())) == 1 and min(by_glass.values()) >= 1
        ctx.check(ids[0], recipe >= 1 and same and pane == 1,
                  'chemical plant recipes that make the laminate %d; as an input: %s; glass pane %d (the original takes blockGlass, not panes; the one '
                  'recipe for a pane is the polarized glass)' % (
                      recipe, by_glass, pane))

        title = translated(ctx, TITLE_CHEMPLANT)[TITLE_CHEMPLANT]
        hud, ok = show_page(ctx, LAMINATE, 'output', lambda t: any(title in x for x in t), len(made.get('categories') or {}))
        if not ok:
            ctx.not_run(ids[1], 'the chemical plant page (title "%s") did not come up for the laminate; categories %s, screen %s, texts %s' % (
                title, list((made.get('categories') or {})), hud.get('screen'), texts_of(hud)[:12]))
            return
        series = ctx.step('series', file=ctx.shot_name('laminate-cycle'), count=4, interval=30)
        files = [i['file'] for i in series['images']]
        ctx.review(ids[1], 'JEI chemical plant page of the reinforced laminate, four pictures 1.5 s apart: in the first of the two item input slots '
                           '(the glass slot, left) each picture must show a different glass (plain, boron, lead, ...) while the second input slot (steel '
                           'bolts) and the output do not change', files)
    section(ctx, ids, body)


def potato(ctx):
    ids = ['rbmk-outgasser.jei-potato', 'rbmk-outgasser.jei-potato-page']

    def body():
        as_input = lookup(ctx, 'minecraft:potato', 'input')
        as_output = lookup(ctx, 'minecraft:poisonous_potato', 'output')
        control = lookup(ctx, 'minecraft:carrot', 'input')
        a, b, c = rows(as_input, IRRADIATION), rows(as_output, IRRADIATION), rows(control, IRRADIATION)
        ctx.check(ids[0], a >= 1 and b >= 1 and c == 0,
                  'irradiation recipes: potato as input %d, poisonous potato as output %d, carrot as input %d (a control with no row); categories of the potato %s' % (
                      a, b, c, list((as_input.get('categories') or {}))))

        title = translated(ctx, TITLE_OUTGASSER)[TITLE_OUTGASSER]
        hud, ok = show_page(ctx, 'minecraft:potato', 'input', lambda t: any(title in x for x in t), len(as_input.get('categories') or {}))
        if not ok:
            ctx.not_run(ids[1], 'the irradiation page (title "%s") did not come up for the potato; categories %s, screen %s, texts %s' % (
                title, list((as_input.get('categories') or {})), hud.get('screen'), texts_of(hud)[:12]))
            return
        ctx.review(ids[1], 'JEI irradiation channel page of the potato (title "%s"): a potato in the input slot on the left, the irradiation channel '
                           'under the arrow, a poisonous potato in the output slot on the right' % title, [shot(ctx, 'irradiation-potato')])
    section(ctx, ids, body)


def sellafield(ctx):
    ids = ['centrifuge.jei-sellafield-lookup', 'centrifuge.jei-sellafield-page']

    def body():
        problems = []
        inputs = {}
        for ore, _ in SELLAFIELD:
            n = rows(lookup(ctx, ore, 'input'), CENTRIFUGE)
            inputs[ore.split(':')[1]] = n
            if n < 1:
                problems.append('%s has no centrifuge recipe as an input' % ore)
        outputs = {}
        for powder, least in POWDER_ROWS_MIN.items():
            n = rows(lookup(ctx, powder, 'output'), CENTRIFUGE)
            outputs[powder.split(':')[1]] = n
            if n < least:
                problems.append('%s is the output of %d centrifuge recipes, expected at least %d' % (powder, n, least))
        ctx.check(ids[0], not problems, '%s; recipes by input %s; recipes by powder output %s' % ('; '.join(problems) or 'all as expected', inputs, outputs))

        title = translated(ctx, TITLE_CENTRIFUGE)[TITLE_CENTRIFUGE]
        pages, missed = [], []
        for ore, powder in SELLAFIELD:
            categories = len(lookup(ctx, ore, 'input').get('categories') or {})
            hud, ok = show_page(ctx, ore, 'input', lambda t: any(title in x for x in t), categories)
            if not ok:
                missed.append('%s (screen %s, texts %s)' % (ore, hud.get('screen'), texts_of(hud)[:8]))
                ctx.step('close', allow_fail=True)
                continue
            pages.append(shot(ctx, 'sellafield-%s' % ore.split(':')[1]))
            ctx.step('close')
        if missed:
            ctx.not_run(ids[1], 'the centrifuge page (title "%s") did not come up for %s' % (title, '; '.join(missed)))
            return
        ctx.review(ids[1], 'three JEI centrifuge pages, in order sellafield diamond ore, sellafield emerald ore, diamond gravel: the input slot holds that '
                           'block; the first three output slots hold the same powder three times (diamond, emerald, diamond) and the fourth holds gravel',
                   pages)
    section(ctx, ids, body)


def burn_times(ctx):
    ids = ['basic-carbon-materials.jei-burn-times']

    def body():
        got, problems = {}, []
        shots = []
        for item, burn in BURN:
            want = burn // 200
            first = lookup(ctx, item, 'input')
            hud, ok = show_page(ctx, item, 'input', lambda t: any(SMELTS.search(x) or SMELTS_ONE.search(x) for x in t), len(first.get('categories') or {}))
            if not ok:
                problems.append('%s: no fuel page (categories %s, screen %s)' % (item, list((first.get('categories') or {})), hud.get('screen')))
                ctx.step('close', allow_fail=True)
                continue
            counts = []
            for x in texts_of(hud):
                m = SMELTS.search(x)
                if m:
                    counts.append(float(m.group(1).replace(',', '')))
                elif SMELTS_ONE.search(x):
                    counts.append(1.0)
            got[item.split(':')[1]] = counts
            if want not in counts:
                problems.append('%s burns %d ticks: the page prints %s, expected %d' % (item, burn, counts, want))
            shots.append(shot(ctx, 'burn-%s' % item.split(':')[1]))
            ctx.step('close')
        ctx.check(ids[0], not problems and len(got) == len(BURN), '%s; fuel pages print %s' % ('; '.join(problems) or 'every page prints burn / 200', got), shots)
    section(ctx, ids, body)


def run(ctx):
    _lib.setup_world(ctx, freeze=False)
    ctx.step('wait', ticks=20)
    for part in (centrifuge_gravel, fuel_recipes, laminate, potato, sellafield, burn_times):
        part(ctx)
