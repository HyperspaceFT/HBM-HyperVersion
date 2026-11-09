#!/usr/bin/env python3
"""Commands that load one assembly-machine recipe into a placed machine (ported from Goal 28's assgen.py).

Usage (from the NEO root): assgen.py RECIPE_NAME [TAG_ITEM ...] --pos X Y Z [--config DIR]
Reads _hbmAssemblyMachine.json from the run's config (default run/config/hbmRecipes, written when the game starts),
prints the recipe duration, then the commands: set recipe0, clear slots 4-16, fill the inputs. Tag inputs map to the
items in TAGS; other tags take the extra TAG_ITEM arguments in input order, or print UNKNOWN. Commands have no leading
"/" so the output can go straight to `rcon.py -f`; add --slash for chat.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

TAGS = {'ntm:ingots_bismoid_bronze': 'hbmsntm:ingot_arsenic_bronze', 'c:plates/steel': 'hbmsntm:plate_steel',
        'c:plates/copper': 'hbmsntm:plate_copper', 'c:plates/titanium': 'hbmsntm:plate_titanium',
        'c:plates/iron': 'hbmsntm:plate_iron', 'ntm:any_rubbers': 'hbmsntm:ingot_rubber',
        'ntm:ingots_resistant_alloy': 'hbmsntm:ingot_cdalloy', 'ntm:ingots_plastic_explosive': 'hbmsntm:ingot_semtex',
        'ntm:ingots_plastic': 'hbmsntm:ingot_polymer'}


def commands(recipe, pos, extra):
    x, y, z = pos
    out = ['data merge block %d %d %d {recipe0:"%s"}' % (x, y, z, recipe['name'])]
    out += ['item replace block %d %d %d container.%d with air' % (x, y, z, i) for i in range(4, 17)]
    for i, row in enumerate(recipe['inputItem']):
        if row[0] == 'tag':
            item = TAGS.get(row[1]) or (extra[i] if i < len(extra) else None) or 'UNKNOWN:' + row[1]
            count, meta = row[2], None
        else:
            item, count = row[1], row[2]
            meta = row[3] if len(row) > 3 and row[3] != 32767 else None
        out.append('item replace block %d %d %d container.%d with %s%s %d'
                   % (x, y, z, 4 + i, item, '[hbmsntm:meta=%d]' % meta if meta is not None else '', count))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('recipe')
    ap.add_argument('tag_items', nargs='*')
    ap.add_argument('--pos', nargs=3, type=int, required=True)
    ap.add_argument('--config', default='run/config/hbmRecipes')
    ap.add_argument('--slash', action='store_true')
    a = ap.parse_args(argv)
    data = json.loads((common.resolve(a.config) / '_hbmAssemblyMachine.json').read_text(encoding='utf-8'))['recipes']
    match = [r for r in data if r['name'] == a.recipe]
    if not match:
        raise SystemExit('no assembly recipe named ' + a.recipe)
    sys.stdout.reconfigure(encoding='utf-8')
    print('# duration', match[0]['duration'])
    for line in commands(match[0], a.pos, a.tag_items):
        print(('/' if a.slash else '') + line)
    return 0


if __name__ == '__main__':
    sys.exit(main())
