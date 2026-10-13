"""Goal19A pollution worlds, assembled from existing suites without changing their modules.

* turbofan: the Goal17B machine world (goal17b_regression.machine_stubs over the Goal15A/14C machine world) with the production
  MachineTurbofanBlockEntity; PollutionHandler records every call, FT_Polluting carries the production burn()/release() bodies and
  KEROSENE the production P_FUEL chain (goal11a_regression.stubs.pollution_handler/ft_polluting).
* oilburner: the Goal 11A machine world (goal11a_regression.stubs.build_stubs, verify_goal11a PRODUCTION/FIXTURES) with the
  production HeaterOilburnerBlockEntity and OIL/HEATINGOIL/GAS carrying their production P_OIL/P_GAS chains.
* traits: the Goal19A barrel world (goal19a_regression.stubs.barrel_world) with the production FT_Polluting and FluidTrait, plus
  the generated Goal19AFlue whose FT_Polluting chain is the production FLUE row of Fluids.java.
"""
from pathlib import Path
import re
import zipfile

FIXTURE = Path(__file__).resolve().parent
TOOLS = FIXTURE.parent
TURBOFAN_BE = 'com/hbm/blockentity/machine/MachineTurbofanBlockEntity.java'
OILBURNER_BE = 'com/hbm/blockentity/machine/heater/HeaterOilburnerBlockEntity.java'
FT_POLLUTING = 'com/hbm/inventory/fluid/trait/FT_Polluting.java'
FLUIDS = 'com/hbm/inventory/fluid/Fluids.java'
POLLUTION = 'com/hbm/handler/pollution/PollutionHandler.java'
FLUE_CLASS = 'com/hbm/inventory/fluid/trait/Goal19AFlue.java'


def turbofan_world(source, sources_jar):
    """(stubs, production, fixtures, main class) of the Goal17B machine world plus Goal19APollutionTurbofan."""
    from goal17b_regression.machine_stubs import machine_stubs, MACHINE_SOURCES
    from goal14a_regression.stubs import NEW_SOURCES
    from verify_goal13a import PRODUCTION as MACHINE_BASE, FIXTURE11A, FIXTURES11A
    fixtures = [FIXTURE11A / p for p in FIXTURES11A] + [TOOLS / 'goal14c_regression/Goal14CMachineRegression.java']
    fixtures += [TOOLS / 'goal17b_regression' / p for p in ('Goal17BMachineRegression.java', 'Goal17BEntityRegression.java')]
    fixtures += [FIXTURE / 'Goal19APollutionTurbofan.java']
    with zipfile.ZipFile(sources_jar) as jar:
        tags = jar.read('net/minecraft/data/tags/VanillaBlockTagsProvider.java').decode('utf-8')
    stubs = machine_stubs(source, [p.read_text(encoding='utf-8') for p in fixtures], tags, sources_jar)
    production = tuple(dict.fromkeys((*MACHINE_BASE, *NEW_SOURCES, *MACHINE_SOURCES)))
    return stubs, production, fixtures, 'com.hbm.blockentity.machine.Goal19APollutionTurbofan'


def oilburner_world(source, sources_jar):
    """(stubs, production, fixtures, main class) of the Goal 11A machine world plus Goal19APollutionOilburner."""
    from goal11a_regression.stubs import build_stubs
    from verify_goal11a import PRODUCTION, FIXTURES, FIXTURE as FIXTURE11A, ANVIL, baseline
    with zipfile.ZipFile(sources_jar) as jar:
        tags = jar.read('net/minecraft/data/tags/VanillaBlockTagsProvider.java').decode('utf-8')
    head_anvil = baseline(ANVIL, 'com.hbm.inventory.recipes.anvil', 'goal11a.head')
    stubs = build_stubs(source, [head_anvil], tags)
    stubs['goal11a/head/AnvilRecipes.java'] = head_anvil
    fixtures = [FIXTURE11A / p for p in FIXTURES] + [FIXTURE / 'Goal19APollutionOilburner.java']
    return stubs, PRODUCTION, fixtures, 'com.hbm.blockentity.machine.Goal19APollutionOilburner'


def flue_chain(fluids_text):
    """The FT_Polluting chain of the production FLUE row, with SOOT_GAS replaced by its production definition."""
    row = re.search(r'^\s*FLUE\s*=\s*new FluidType\(.*?new FT_Polluting\(\)((?:\.(?:burn|release)\(PollutionType\.[A-Z]+, [A-Z_]+(?: \* [0-9.]+F?)?\))+)\);',
                    fluids_text, re.M)
    if not row: raise SystemExit('Goal19A: FLUE FT_Polluting row not found in Fluids.java')
    chain = row.group(1)
    constants = dict(re.findall(r'public static final float ((?:SOOT|POISON|LEAD)_[A-Z_]+) = ([^;]+);', fluids_text))
    for name in sorted(set(re.findall(r'\b((?:SOOT|POISON|LEAD)_[A-Z_]+)\b', chain))):
        if name not in constants: raise SystemExit('Goal19A: FLUE constant not found: ' + name)
        chain = re.sub(r'\b' + name + r'\b', '(' + constants[name] + ')', chain)
    return row.group(1), chain


def flue_class(fluids_text):
    return ('package com.hbm.inventory.fluid.trait;import com.hbm.handler.pollution.PollutionHandler;import com.hbm.handler.pollution.PollutionHandler.PollutionType;\n'
            '/** Generated from the production FLUE row of Fluids.java. */\npublic class Goal19AFlue{public static FT_Polluting flue(){return new FT_Polluting()'
            + flue_chain(fluids_text)[1] + ';}}')


def traits_world(source, overrides=None):
    """(stubs, production, fixtures, main class) of the Goal19A barrel world plus Goal19AFlue and Goal19APollutionTraits."""
    from goal19a_regression.stubs import barrel_world, PRODUCTION as BARREL_PRODUCTION
    from verify_goal7b import PRODUCTION as GOAL7B_PRODUCTION
    overrides = overrides or {}
    stubs, _ = barrel_world(source)
    pollution = (source / POLLUTION).read_text(encoding='utf-8')
    # The barrel world's PollutionHandler stand-in hard-codes the rate the FLUE constant is built from.
    if 'public static final float SOOT_PER_SECOND = 1F / 25F;' not in pollution or 'SOOT_PER_SECOND=1F / 25F' not in stubs[POLLUTION]:
        raise SystemExit('Goal19A: SOOT_PER_SECOND differs between production and the barrel-world stand-in')
    fluids = overrides.get(FLUIDS) or (source / FLUIDS).read_text(encoding='utf-8')
    stubs[FLUE_CLASS] = flue_class(fluids)
    production = tuple(dict.fromkeys((*GOAL7B_PRODUCTION, *BARREL_PRODUCTION)))
    return stubs, production, [FIXTURE / 'Goal19APollutionTraits.java'], 'com.hbm.inventory.fluid.trait.Goal19APollutionTraits'
