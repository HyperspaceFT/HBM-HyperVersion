#!/usr/bin/env python3
"""Survival-source closure: for each item in a list, is there a way to get it in survival, and through what chain?

Run from the NEO root:
  python3 -B -X utf8 tools/migration/acceptance/closure.py --recipes-export build/migration/accept-goal29/clients/g31e_solo/config/hbmRecipes \\
      hbmsntm:settings_tool hbmsntm:part_generic@0 hbmsntm:fluorite hbmsntm:machine_zirnox
  ... --items-file items.txt --json out.json

Sources, read from the data the mod ships (no game run):
  - every minecraft: item is taken as obtainable (vanilla survival; creative-only vanilla items are not modelled);
  - world generation: blocks placed by the configured features that a placed feature uses and a biome modifier or a
    biome lists, from both src/main/resources and src/generated/resources (the hand-written ores live in the former),
    turned into items by the blocks' loot tables;
  - loot tables under loot_table/chests and loot_table/entities (taken as reachable; the report names them);
  - crafting and smelting recipe JSON (shaped, shapeless, smelting, blasting, smoking, campfire, stonecutting), with
    item tags from the mod's data, NeoForge's jar (c:) and Minecraft's resources jar (minecraft:);
  - the machine recipe tables, which are defined in Java and only exist as JSON after a game run writes them to
    config/hbmRecipes: --recipes-export names such a directory (a client's or the server's), and the report records it
    with the file hashes and the build that wrote it (--export-build, default: the current build/libs jar);
  - the anvil's construction and smithing recipes, which no game run writes as JSON: --anvil-export takes the file the
    acceptance executor's export step writes (exports/anvil.json in its step directory);
  - the crucible: --crucible-export takes the export step's exports/crucible.json (which items melt into which
    materials, by the crucible's own rule, and what each mold casts from each material); the alloy recipes come from
    _hbmCrucible.json in the machine-recipe export. Materials show up in chains as material:<Name>; melting needs
    the crucible, a cast needs its mold item (the foundry blocks around them are not checked).
A recipe makes its output obtainable when every item ingredient is; machines are listed in the chain, but whether the
machine itself is obtainable is only checked for the machines in MACHINES, and fluid inputs are not checked (both
reported). Items with a meta variant are written id@meta (part_generic@0 is the pneumatic piston); a plain id matches any
variant. Python standard library only.
"""
import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

REPO = common.REPO
DATA_ROOTS = [REPO / 'src' / 'main' / 'resources' / 'data', REPO / 'src' / 'generated' / 'resources' / 'data']
ARTIFACTS = REPO / 'build' / 'moddev' / 'artifacts'
JARS = ['neoforge-21.1.228.jar', 'neoforge-21.1.228-client-extra-aka-minecraft-resources.jar']
WILDCARD = 32767
# Machine recipe file -> the machine's item; a recipe of a listed machine also needs the machine.
CRUCIBLE = 'hbmsntm:machine_crucible'
MACHINES = {
    '_hbmAssemblyMachine.json': 'hbmsntm:machine_assembly_machine',
    '_hbmPress.json': 'hbmsntm:machine_press',
    '_hbmShredder.json': 'hbmsntm:machine_shredder',
    '_hbmCentrifuge.json': 'hbmsntm:machine_centrifuge',
    '_hbmCrystallizer.json': 'hbmsntm:machine_crystallizer',
    '_hbmChemicalPlant.json': 'hbmsntm:machine_chemical_plant',
}
INPUT_KEYS = ('input', 'inputItem', 'inputs', 'solidInput', 'pcb', 'solder', 'toppings')
# the arc furnace writes its item result under `solid` (ArcFurnaceRecipes.java:121-135)
OUTPUT_KEYS = ('output', 'outputItem', 'outputs', 'byproduct', 'solidOutput', 'solid')
COOKING = ('minecraft:smelting', 'minecraft:blasting', 'minecraft:smoking', 'minecraft:campfire_cooking', 'minecraft:stonecutting')


def base(item):
    return item.split('@', 1)[0]


class Data:
    def __init__(self):
        self.files = {}      # 'namespace/path' -> json (later roots win, like resource packs)
        self.jar_files = {}

    def load(self):
        for root in DATA_ROOTS:
            if root.is_dir():
                for path in root.rglob('*.json'):
                    self.files[path.relative_to(root).as_posix()] = (json.loads(path.read_text(encoding='utf-8')), common.rel(path))
        for name in JARS:
            jar = ARTIFACTS / name
            if not jar.is_file():
                continue
            with zipfile.ZipFile(jar) as z:
                for entry in z.namelist():
                    if entry.startswith('data/') and '/tags/item' in entry and entry.endswith('.json'):
                        self.jar_files[entry[5:]] = (json.loads(z.read(entry)), '%s!%s' % (name, entry))
        return self

    def under(self, folder):
        """{'ns:path': (json, origin)} for files data/<ns>/<folder>/<path>.json."""
        out = {}
        for key, value in self.files.items():
            ns, _, rest = key.partition('/')
            if rest.startswith(folder + '/'):
                out['%s:%s' % (ns, rest[len(folder) + 1:-5])] = value
        return out

    def tags(self):
        tags = {}
        for source in (self.jar_files, self.files):
            for key, (data, origin) in source.items():
                ns, _, rest = key.partition('/')
                for folder in ('tags/item/', 'tags/items/'):
                    if rest.startswith(folder):
                        name = '%s:%s' % (ns, rest[len(folder):-5])
                        values = tags.setdefault(name, [])
                        if data.get('replace'):
                            values.clear()
                        for v in data.get('values', []):
                            values.append(v['id'] if isinstance(v, dict) else v)
        return tags


def resolve_tag(tags, name, seen=None):
    seen = seen if seen is not None else set()
    if name in seen:
        return set()
    seen.add(name)
    out = set()
    for v in tags.get(name, []):
        out |= resolve_tag(tags, v[1:], seen) if v.startswith('#') else {v}
    return out


def ingredient(tags, value):
    """A recipe JSON ingredient -> set of acceptable items (id or id@meta)."""
    if isinstance(value, list):
        out = set()
        for v in value:
            out |= ingredient(tags, v)
        return out
    if 'tag' in value:
        return resolve_tag(tags, value['tag']) or {'#' + value['tag']}
    if value.get('type') == 'neoforge:components':
        items = value['items'] if isinstance(value['items'], list) else [value['items']]
        meta = value.get('components', {}).get('hbmsntm:meta')
        return {('%s@%s' % (i, meta)) if meta is not None else i for i in items}
    if 'item' in value:
        return {value['item']}
    if 'items' in value:
        return set(value['items'] if isinstance(value['items'], list) else [value['items']])
    return {'?' + json.dumps(value)}


def result_item(value):
    if isinstance(value, str):
        return value
    meta = (value.get('components') or {}).get('hbmsntm:meta')
    rid = value.get('id') or value.get('item')
    return '%s@%s' % (rid, meta) if meta is not None else rid


def crafting_recipes(data, tags):
    recipes = []
    for name, (r, origin) in data.under('recipe').items():
        t = r.get('type')
        if t == 'minecraft:crafting_shaped':
            ings = [ingredient(tags, r['key'][c]) for c in sorted({c for row in r['pattern'] for c in row if c != ' '})]
        elif t == 'minecraft:crafting_shapeless':
            ings = [ingredient(tags, i) for i in r['ingredients']]
        elif t in COOKING:
            ings = [ingredient(tags, r['ingredient'])]
        else:
            continue
        recipes.append(dict(kind=t.split(':')[1], name=name, origin=origin, inputs=ings, outputs={result_item(r['result'])}, machine=None))
    return recipes


def machine_entries(node, found):
    """Ingredient lists inside a machine recipe input: ["item", id, n, meta], ["tag", t, n], ["dict", d, n], [id, n...]."""
    if isinstance(node, list):
        if node and isinstance(node[0], str):
            head = node[0]
            if head == 'item' and len(node) > 1:
                # a missing meta is variant 0 (SerializableRecipe.readAStack); only the wildcard takes any variant
                meta = node[3] if len(node) > 3 and isinstance(node[3], int) else 0
                found.append({node[1] if meta == WILDCARD else '%s@%s' % (node[1], meta)})
                return
            if head in ('tag', 'dict') and len(node) > 1:
                found.append({'#' + node[1]})
                return
            if ':' in head:
                found.append({'%s@0' % head})
                return
        for child in node:
            machine_entries(child, found)
    elif isinstance(node, dict):
        for child in node.values():
            machine_entries(child, found)


def machine_outputs(node, found):
    """Item ids in a machine recipe output; [id, count, meta] carries a variant in its third place (an int)."""
    if isinstance(node, str):
        if ':' in node:
            found.add(node)
    elif isinstance(node, list):
        if len(node) >= 3 and isinstance(node[0], str) and ':' in node[0] and isinstance(node[2], int) and node[2] != WILDCARD:
            found.add('%s@%s' % (node[0], node[2]))
            return
        for child in node:
            machine_outputs(child, found)
    elif isinstance(node, dict):
        for child in node.values():
            machine_outputs(child, found)


def machine_recipes(export, tags):
    recipes, files = [], {}
    if not export:
        return recipes, files
    for path in sorted(Path(export).glob('*.json')):
        files[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        data = json.loads(path.read_text(encoding='utf-8'))
        entries = data.get('recipes', []) if isinstance(data, dict) else data
        for n, r in enumerate(entries if isinstance(entries, list) else []):
            ings = []
            for key in INPUT_KEYS:
                if key in r:
                    machine_entries(r[key], ings)
            ings = [expand(tags, i) for i in ings]
            if isinstance(r.get('stamp'), str):
                ings.append({'stamp:' + r['stamp']})  # any stamp item of that type, resolved in closure()
            outs = set()
            for key in OUTPUT_KEYS:
                if key in r:
                    machine_outputs(r[key], outs)
            if outs:
                recipes.append(dict(kind='machine', name='%s#%s' % (path.name, r.get('name', n)), origin=common.rel(path),
                                    inputs=ings, outputs=outs, machine=MACHINES.get(path.name), fluids=any(k in r for k in ('inputFluid', 'fluid'))))
    return recipes, files


def anvil_recipes(path):
    """The executor's export of the anvil tables (export step): construction and smithing recipes."""
    recipes = []
    if not path:
        return recipes, None
    data = json.loads(Path(path).read_text(encoding='utf-8'))

    def key(s):
        return stack_key(s)
    for kind in ('construction', 'smithing'):
        for n, r in enumerate(data.get(kind, [])):
            recipes.append(dict(kind='anvil ' + kind, name='anvil %s #%d (tier %s)' % (kind, n, r.get('tier_lower')),
                                origin=common.rel(Path(path)), inputs=[{stack_key(s, exact=True) for s in alts} for alts in r['inputs'] if alts],
                                outputs={key(s) for s in r['outputs']}, machine=None))
    return recipes, hashlib.sha256(Path(path).read_bytes()).hexdigest()


def stack_key(s, exact=False):
    """An exported stack: meta 32767 is the wildcard (any variant). As an output, meta 0 is the plain item; as an exact
    input (exact=True) it is variant 0, which a variant 5 of the same item does not satisfy."""
    if s.get('meta') == WILDCARD:
        return s['id']
    if not s.get('meta') and not exact:
        return s['id']
    return '%s@%s' % (s['id'], s.get('meta') or 0)


def crucible_recipes(path, export):
    """Melting and casting from the executor's crucible export, alloys from the machine export's _hbmCrucible.json."""
    recipes = []
    if export and (Path(export) / '_hbmCrucible.json').is_file():
        alloys = Path(export) / '_hbmCrucible.json'
        for r in json.loads(alloys.read_text(encoding='utf-8')).get('recipes', []):
            recipes.append(dict(kind='crucible alloy', name='_hbmCrucible.json#%s' % r.get('name'), origin=common.rel(alloys),
                                inputs=[{'material:' + m[0]} for m in r.get('input', [])],
                                outputs={'material:' + m[0] for m in r.get('output', [])}, machine=CRUCIBLE))
    if not path:
        return recipes, None
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    origin = common.rel(Path(path))
    for r in data.get('smelting', []):
        item = stack_key(r['item'], exact=True)
        recipes.append(dict(kind='crucible melting', name='melting %s' % item, origin=origin, inputs=[{item}],
                            outputs={'material:' + m[0] for m in r['materials']}, machine=CRUCIBLE))
    for c in data.get('casts', []):
        recipes.append(dict(kind='cast', name='cast %s' % c['material'], origin=origin, inputs=[{'material:' + c['material']}],
                            outputs={stack_key(c['output'])}, machine=c['mold']))
    return recipes, hashlib.sha256(Path(path).read_bytes()).hexdigest()


def expand(tags, alternatives):
    out = set()
    for a in alternatives:
        out |= (resolve_tag(tags, a[1:]) or {a}) if a.startswith('#') else {a}
    return out


def worldgen_sources(data):
    """{block id: [placed feature, ...]} for blocks the world generator places."""
    biome_refs = set()
    for name, (m, origin) in list(data.under('neoforge/biome_modifier').items()) + list(data.under('worldgen/biome').items()):
        if isinstance(m, dict) and m.get('type') == 'neoforge:remove_features':
            continue
        biome_refs |= {s for s in collect_strings(m) if ':' in s}
    placed = data.under('worldgen/placed_feature')
    configured = data.under('worldgen/configured_feature')
    out = {}
    for pname, (p, origin) in placed.items():
        if pname not in biome_refs:
            continue
        feature = p.get('feature')
        cf = configured.get(feature)[0] if isinstance(feature, str) and feature in configured else feature
        for s in states(cf):
            out.setdefault(s, []).append(pname)
    return out


def collect_strings(node):
    if isinstance(node, str):
        yield node
    elif isinstance(node, list):
        for c in node:
            yield from collect_strings(c)
    elif isinstance(node, dict):
        for c in node.values():
            yield from collect_strings(c)


def states(node):
    """Block names of every block state in a configured feature (ore targets, state providers)."""
    if isinstance(node, dict):
        if 'Name' in node and isinstance(node['Name'], str):
            yield node['Name']
        for k, c in node.items():
            if k not in ('target', 'predicate'):  # the block an ore replaces is not placed
                yield from states(c)
    elif isinstance(node, list):
        for c in node:
            yield from states(c)


def loot_items(table):
    found = set()

    def walk(n):
        if isinstance(n, dict):
            if n.get('type') == 'minecraft:item' and 'name' in n:
                metas = [f.get('components', {}).get('hbmsntm:meta') for f in n.get('functions', [])
                         if isinstance(f, dict) and f.get('function') == 'minecraft:set_components']
                metas = [m for m in metas if isinstance(m, int)]
                found.add('%s@%s' % (n['name'], metas[-1]) if metas else n['name'])
            for c in n.values():
                walk(c)
        elif isinstance(n, list):
            for c in n:
                walk(c)
    walk(table)
    return found


def closure(targets, export, anvil=None, data=None, crucible=None):
    data = data or Data().load()
    tags = data.tags()
    recipes = crafting_recipes(data, tags)
    mrecipes, export_files = machine_recipes(export, tags)
    recipes += mrecipes
    arecipes, anvil_hash = anvil_recipes(anvil)
    recipes += arecipes
    crecipes, crucible_hash = crucible_recipes(crucible, export)
    recipes += crecipes
    known = {base(o) for r in recipes for o in r['outputs']}
    for r in recipes:
        r['inputs'] = [({i for i in known if i.startswith('hbmsntm:stamp_') and i.endswith('_' + next(iter(alts))[6:])}
                        or alts) if len(alts) == 1 and next(iter(alts)).startswith('stamp:') else alts for alts in r['inputs']]
    loot = data.under('loot_table')
    how = {}

    def give(item, reason):
        if item not in how:
            how[item] = reason
            if '@' in item and base(item) not in how:
                how[base(item)] = reason
            if '@' not in item and item + '@0' not in how:
                how[item + '@0'] = reason  # a stack without the meta component is variant 0

    gen = worldgen_sources(data)
    for block, features in gen.items():
        table = loot.get('%s:blocks/%s' % tuple(block.split(':', 1)))
        drops = loot_items(table[0]) if table else ({block} if block.startswith('minecraft:') else set())
        for item in drops:
            give(item, dict(kind='worldgen', block=block, features=sorted(set(features))[:3],
                            loot=table[1] if table else None))
    for name, (table, origin) in loot.items():
        if '/chests/' in name.replace(':', '/') or '/entities/' in name.replace(':', '/'):
            for item in loot_items(table):
                give(item, dict(kind='loot', table=name, origin=origin))

    def have(item):
        return item in how or base(item).startswith('minecraft:') or (('@' not in item) and any(k.startswith(item + '@') for k in how))

    changed = True
    while changed:
        changed = False
        for r in recipes:
            if all(o in how for o in r['outputs']):
                continue
            if r['machine'] and not have(r['machine']):
                continue
            if all(any(have(a) for a in alts) for alts in r['inputs']):
                for o in r['outputs']:
                    if o not in how:
                        give(o, dict(kind=r['kind'], recipe=r['name'], origin=r['origin'], machine=r['machine'],
                                     fluids_unchecked=r.get('fluids', False),
                                     inputs=[sorted(a)[:4] for a in r['inputs']]))
                        changed = True

    def chain(item, depth, seen):
        reason = how.get(item) or how.get(base(item))
        if base(item).startswith('minecraft:') and not reason:
            return dict(item=item, kind='vanilla')
        if not reason:
            return dict(item=item, kind='none')
        node = dict(item=item, **{k: v for k, v in reason.items() if k != 'inputs'})
        if depth > 0 and 'inputs' in reason and item not in seen:
            node['from'] = []
            for alts in reason['inputs']:
                pick = next((a for a in alts if have(a)), alts[0])
                node['from'].append(chain(pick, depth - 1, seen | {item}))
        return node

    report = []
    for t in targets:
        if have(t):
            report.append(dict(item=t, obtainable=True, chain=chain(t, 6, frozenset())))
        else:
            missing = []
            for r in recipes:
                if t in r['outputs']:
                    missing.append(dict(recipe=r['name'], machine=r['machine'],
                                        missing=[sorted(a)[:4] for a in r['inputs'] if not any(have(x) for x in a)]))
            report.append(dict(item=t, obtainable=False, recipes_without_sources=missing[:5]))
    return dict(targets=report, recipe_count=len(recipes), machine_recipe_count=len(mrecipes), anvil_recipe_count=len(arecipes),
                worldgen_blocks=len(gen), export=common.rel(Path(export)) if export else None, export_files=export_files,
                anvil_export=common.rel(Path(anvil)) if anvil else None, anvil_export_sha256=anvil_hash,
                crucible_recipe_count=len(crecipes), crucible_export=common.rel(Path(crucible)) if crucible else None,
                crucible_export_sha256=crucible_hash)


def text_chain(node, indent=0):
    pad = '  ' * indent
    k = node['kind']
    if k == 'vanilla':
        line = '%s%s: vanilla' % (pad, node['item'])
    elif k == 'none':
        line = '%s%s: NO SOURCE' % (pad, node['item'])
    elif k == 'worldgen':
        line = '%s%s: world generation, block %s (%s)' % (pad, node['item'], node['block'], ', '.join(node['features']))
    elif k == 'loot':
        line = '%s%s: loot table %s' % (pad, node['item'], node['table'])
    else:
        line = '%s%s: %s %s%s%s' % (pad, node['item'], k, node['recipe'], ' in ' + node['machine'] if node.get('machine') else '',
                                     ' (fluid inputs not checked)' if node.get('fluids_unchecked') else '')
    lines = [line]
    for child in node.get('from', []):
        lines += text_chain(child, indent + 1)
    return lines


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('items', nargs='*')
    ap.add_argument('--items-file')
    ap.add_argument('--recipes-export', help='a config/hbmRecipes directory written by a game run')
    ap.add_argument('--anvil-export', help='exports/anvil.json written by the executor\'s export step')
    ap.add_argument('--crucible-export', help='exports/crucible.json written by the executor\'s export step (kind crucible)')
    ap.add_argument('--export-build', help='text recorded as the build that wrote the export (default: the current build/libs jar hash)')
    ap.add_argument('--json', help='write the full report here')
    args = ap.parse_args(argv)
    items = list(args.items)
    if args.items_file:
        items += [l.strip() for l in Path(args.items_file).read_text(encoding='utf-8').splitlines() if l.strip() and not l.startswith('#')]
    if not items:
        raise SystemExit('no items')
    export = common.resolve(args.recipes_export) if args.recipes_export else None
    if export and not export.is_dir():
        raise SystemExit('no export directory ' + str(export))
    anvil = common.resolve(args.anvil_export) if args.anvil_export else None
    crucible = common.resolve(args.crucible_export) if args.crucible_export else None
    report = closure(items, export, anvil, crucible=crucible)
    jars = sorted((REPO / 'build' / 'libs').glob('*.jar'))
    report['export_build'] = args.export_build or ('build/libs %s sha256 %s' % (jars[0].name, common.sha256(jars[0])) if jars else 'unknown')
    for t in report['targets']:
        if t['obtainable']:
            print('\n'.join(text_chain(t['chain'])))
        else:
            print('%s: NO SURVIVAL SOURCE; recipes with missing inputs: %s' % (t['item'], json.dumps(t['recipes_without_sources'])[:500]))
    print('-- %d recipes (%d machine recipes from %s, %d anvil recipes from %s, %d crucible recipes from %s), %d world-generated '
          'blocks; export build: %s' % (
              report['recipe_count'], report['machine_recipe_count'], report['export'], report['anvil_recipe_count'], report['anvil_export'],
              report['crucible_recipe_count'], report['crucible_export'], report['worldgen_blocks'], report['export_build']))
    if args.json:
        common.write_json(common.resolve(args.json), report)
    return 0 if all(t['obtainable'] for t in report['targets']) else 1


if __name__ == '__main__':
    sys.exit(main())
