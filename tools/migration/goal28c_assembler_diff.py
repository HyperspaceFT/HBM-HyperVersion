"""Goal28C: assembly machine recipe difference between the original and NEO, by recipe name and product registry name.

Reads only the two AssemblyMachineRecipes.java files and NEO's NtmItems.java / NtmBlocks.java (registry names), never a
language key, so products without a language key (the two radars) and renamed recipes are matched. Each original row is
classified as:
  registered       a NEO row has the same recipe name
  renamed          no NEO row has the name, but a NEO row whose name is not an original recipe name makes the same product
                   registry name (listed with the NEO name); a NEO row that is itself an original recipe is an alternative, not a rename
  candidate        no NEO row by name or product, and the product registry name is registered in NEO
  unregistered     the product is not registered in NEO
  unresolved       the product could not be read statically (a loop or a variable stack)
Original circuit meta items (ModItems.circuit + EnumCircuitType) map to NEO's separate circuit_* items through CIRCUITS,
taken from the English names (original en_US.lang:2439-2459, NEO NtmLanguageProvider.java:764-782).

Run from the NEO repository root (read-only except the output):
    python -B -X utf8 tools/migration/goal28c_assembler_diff.py [--output build/migration/goal28c/assembler-diff.json]
"""
from pathlib import Path
import json, re, sys

ROOT = Path.cwd()
SOURCE = ROOT.parent / 'Hbm-s-Nuclear-Tech-GIT'
ORIGINAL_AMR = SOURCE / 'src/main/java/com/hbm/inventory/recipes/AssemblyMachineRecipes.java'
NEO_AMR = ROOT / 'src/main/java/com/hbm/inventory/recipes/AssemblyMachineRecipes.java'
NEO_ITEMS = ROOT / 'src/main/java/com/hbm/items/NtmItems.java'
NEO_BLOCKS = ROOT / 'src/main/java/com/hbm/blocks/NtmBlocks.java'
OUTPUT = Path(sys.argv[sys.argv.index('--output') + 1]) if '--output' in sys.argv else ROOT / 'build/migration/goal28c/assembler-diff.json'

CIRCUITS = {
    'VACUUM_TUBE': 'circuit_vacuum_tube', 'CAPACITOR': 'circuit_capacitor', 'CAPACITOR_TANTALIUM': 'circuit_tantalium_capacitor',
    'PCB': 'circuit_printed_board', 'SILICON': 'circuit_printed_silicon_wafer', 'CHIP': 'circuit_microchip',
    'CHIP_BISMOID': 'circuit_versatile_integrated', 'ANALOG': 'circuit_analog_board', 'BASIC': 'circuit_integrated_board',
    'ADVANCED': 'circuit_military_grade_board', 'CAPACITOR_BOARD': 'circuit_capacitor_board', 'BISMOID': 'circuit_versatile_board',
    'CONTROLLER_CHASSIS': 'circuit_control_unit_casing', 'CONTROLLER': 'circuit_control_unit',
    'CONTROLLER_ADVANCED': 'circuit_advanced_control_unit', 'QUANTUM': 'circuit_quantum_processing_unit',
    'CHIP_QUANTUM': 'circuit_solid_state_quantum_processor', 'CONTROLLER_QUANTUM': 'circuit_quantum_computer',
    'ATOMIC_CLOCK': 'circuit_atomic_clock'}

# Goal28C's decision for every candidate (GOAL28.md decisions 5 and 6, GOAL28C.md C1-C2): 'register' rows are added to NEO's
# AssemblyMachineRecipes in this batch; every other value is the reason the row stays out. A candidate missing here is reported.
DEFER_5 = 'deferred with its system (GOAL28 decision 5: bombs, missiles, launch pads, satellites, PWR)'
FOLLOW_UP = 'outside the fixed 28C scope (GOAL28C C1); recorded as a follow-up candidate'
DECISIONS = dict(
    {n: 'register' for n in ('ass.plateiron', 'ass.plategold', 'ass.platetitanium', 'ass.platealu', 'ass.platesteel', 'ass.platelead',
                             'ass.platecopper', 'ass.plateschrab', 'ass.platecmb', 'ass.plategunmetal', 'ass.platesaturnite', 'ass.platedura',
                             'ass.assembler', 'ass.chemplantAlt', 'ass.pumpjack', 'ass.fracker', 'ass.radar', 'ass.radarlarge',
                             'ass.leviturbine', 'ass.overdrive1', 'ass.overdrive2', 'ass.overdrive3', 'ass.minenaval', 'ass.emptypackage')},
    **{'ass.platemixed': 'Goal28D (needs saturnite plates from the rotary furnace; GOAL28 decision 4)',
       'ass.chipBismoid': 'deferred with its inputs (GOAL13B B4)', 'ass.chipQuantum': 'deferred with its inputs (GOAL13B B4)',
       'ass.atomicClock': 'deferred with its inputs (GOAL13B B4); ass.atomicClockAlt is registered',
       'ass.pistonsetstar': FOLLOW_UP + ' (starmetal ingot)',
       'ass.capacitorgold': FOLLOW_UP + ' (battery_pack capacitor subtype)', 'ass.capacitorniobium': FOLLOW_UP + ' (battery_pack capacitor subtype)',
       'ass.capacitortantalum': FOLLOW_UP + ' (battery_pack capacitor subtype)', 'ass.capacitorbismuth': FOLLOW_UP + ' (battery_pack capacitor subtype)',
       'ass.capacitorspark': FOLLOW_UP + ' (battery_pack capacitor subtype)',
       'ass.alclad': FOLLOW_UP + ' (part_generic ALCLAD subtype)', 'ass.titaniumconstruction': FOLLOW_UP + ' (part_generic ALCLAD subtype)',
       'ass.pwrcontroller': DEFER_5})
for _n in ('ass.gadget', 'ass.ninadidnothingwrong', 'ass.fleija', 'ass.solinium', 'ass.n2mine', 'ass.balefirebomb', 'ass.explosivelenses1',
           'ass.explosivelenses2', 'ass.wiring', 'ass.core1', 'ass.fleijaigniter', 'ass.fleijacore', 'ass.fleijacharge', 'ass.soliniumigniter',
           'ass.soliniumcore', 'ass.soliniumcharge', 'ass.stealthmissile', 'ass.shuttlemissile', 'ass.launchpad', 'ass.launchpadsilo', 'ass.soyuz',
           'ass.spacelab', 'ass.sensorrelay', 'ass.0gassembler', 'ass.spysat', 'ass.scansat', 'ass.radarsat', 'ass.astrominer', 'ass.lunarminer',
           'ass.orbitallaser', 'ass.deathray', 'ass.xenrelay', 'ass.relaysat', 'ass.detectorsat', 'ass.rayscansat'):
    DECISIONS[_n] = DEFER_5

RECIPE = re.compile(r'new GenericRecipe\("([^"]+)"\)')
REG = re.compile(r'public static final Deferred\w+<[^>]+(?:<[^>]*>)?>\s+(\w+)\s*=\s*(?:ITEMS\.register|register\w*)\("([^"]+)"')


def strip_comments(text):
    """Blank out whole-line // comments, keeping the line count so recipe line numbers stay those of the file."""
    return '\n'.join('' if line.lstrip().startswith('//') else line for line in text.splitlines())


def statements(text):
    """Every register(new GenericRecipe("...") ...) statement with its line number, split at the next recipe start."""
    starts = [(m.start(), m.group(1)) for m in RECIPE.finditer(text)]
    out = []
    for i, (pos, name) in enumerate(starts):
        end = starts[i + 1][0] if i + 1 < len(starts) else len(text)
        out.append((name, text.count('\n', 0, pos) + 1, text[pos:end]))
    return out


def original_product(stmt):
    m = re.search(r'outputItems\((.*)', stmt, re.S)
    if not m: return None, 'no outputItems'
    body = m.group(1)
    c = re.match(r'\s*DictFrame\.fromOne\(ModItems\.circuit,\s*EnumCircuitType\.(\w+)', body)
    if c: return CIRCUITS.get(c.group(1)), 'circuit ' + c.group(1)
    s = re.match(r'\s*new ItemStack\(Mod(?:Items|Blocks)\.(\w+)', body) or re.match(r'\s*DictFrame\.fromOne\(Mod(?:Items|Blocks)\.(\w+)', body)
    if s: return s.group(1), None
    return None, 'unresolved: ' + body[:60].replace('\n', ' ')


def neo_product(stmt, regnames):
    m = re.search(r'outputItems\((.*)', stmt, re.S)
    if not m: return None, 'no outputItems'
    s = re.match(r'\s*(?:new ItemStack|MetaHelper\.newStack)\(Ntm(?:Items|Blocks)\.(\w+)', m.group(1))
    if s: return regnames.get(s.group(1)), None
    return None, 'unresolved: ' + m.group(1)[:60].replace('\n', ' ')


def main():
    regnames = {}
    for f in (NEO_ITEMS, NEO_BLOCKS):
        for const, name in REG.findall(f.read_text(encoding='utf-8')): regnames.setdefault(const, name)
    registered = set(regnames.values())
    orig = statements(strip_comments(ORIGINAL_AMR.read_text(encoding='utf-8')))
    neo = statements(strip_comments(NEO_AMR.read_text(encoding='utf-8')))
    neo_rows = []
    for name, line, stmt in neo:
        product, note = neo_product(stmt, regnames)
        neo_rows.append(dict(name=name, line=line, product=product, note=note, dynamic='"+' in stmt[:80] or '" +' in stmt[:80]))
    neo_names = {r['name'] for r in neo_rows}
    orig_names = {name for name, _, _ in orig}
    neo_by_product = {}
    for r in neo_rows:
        if r['product'] and r['name'] not in orig_names: neo_by_product.setdefault(r['product'], []).append(r['name'])
    rows = []
    for name, line, stmt in orig:
        product, note = original_product(stmt)
        if name in neo_names: cls = 'registered'
        elif product is None: cls = 'unresolved'
        elif product in neo_by_product: cls = 'renamed'
        elif product in registered: cls = 'candidate'
        else: cls = 'unregistered'
        rows.append(dict(name=name, line=line, product=product, note=note, cls=cls,
                         neo_names=neo_by_product.get(product, []) if cls == 'renamed' else [],
                         decision=DECISIONS.get(name) if cls == 'candidate' else None,
                         expensive='inputItemsEx' in stmt, pools528='setPools528' in stmt,
                         pools=re.findall(r'setPools\(([^)]*)\)', stmt)))
    counts = {}
    for r in rows: counts[r['cls']] = counts.get(r['cls'], 0) + 1
    report = dict(
        original=str(ORIGINAL_AMR.relative_to(ROOT.parent)).replace('\\', '/'), neo=str(NEO_AMR.relative_to(ROOT)).replace('\\', '/'),
        original_rows=len(rows), neo_rows=len(neo_rows), counts=counts,
        neo_only=[r['name'] for r in neo_rows if r['name'] not in orig_names],
        candidates=[r for r in rows if r['cls'] == 'candidate'],
        register=[r['name'] for r in rows if r['cls'] == 'candidate' and DECISIONS.get(r['name']) == 'register'],
        undecided=[r['name'] for r in rows if r['cls'] == 'candidate' and r['name'] not in DECISIONS],
        stale_decisions=sorted(n for n in DECISIONS if n not in {r['name'] for r in rows if r['cls'] in ('candidate', 'registered')}),
        renamed=[r for r in rows if r['cls'] == 'renamed'],
        unresolved=[r for r in rows if r['cls'] == 'unresolved'],
        rows=rows, neo_table=neo_rows)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(original_rows=len(rows), neo_rows=len(neo_rows), counts=counts, register=len(report['register']),
                          undecided=report['undecided'], stale_decisions=report['stale_decisions']), ensure_ascii=False))
    for r in report['candidates']: print('candidate', r['name'], r['product'], 'L%d' % r['line'], 'EX' if r['expensive'] else '', '528' if r['pools528'] else '', '|', r['decision'])
    for r in report['renamed']: print('renamed', r['name'], '->', ','.join(r['neo_names']), r['product'])
    for r in report['unresolved']: print('unresolved', r['name'], r['note'])


if __name__ == '__main__':
    main()
