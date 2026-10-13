"""Goal19A stray cog / pumpjack worlds, built from the existing Goal 8 and Goal 11A worlds without changing them.

* Cog world: the Goal 8 world as it is (production StrayCog over the Goal 8 ProjectileNT, Level, BlockState and explosion
  stand-ins), reached through the unchanged goal8_regression accessor Goal8CogAccess.
* Pumpjack world: the Goal 11A machine world (production OilDrillBaseBlockEntity, DummyableBlock bodies, MachineOilWellBlock)
  plus the production MachinePumpjackBlockEntity; only its block entity type is added to NtmBlockEntityTypes. The core
  state comes from the production DummyableBlock.createCoreState of the compiled derrick block, which carries FACING as
  MachinePumpjackBlock's does; MachinePumpjackBlock itself is not compiled (MultiblockHandlerXR and its tooltips are
  outside both worlds).
"""

from goal8_regression.stubs import build_stubs as goal8_stubs
from goal11a_regression.stubs import build_stubs as goal11a_stubs

PUMPJACK_BE = "com/hbm/blockentity/machine/oil/MachinePumpjackBlockEntity.java"


def cog_stubs(source):
    return goal8_stubs(source)


def pumpjack_stubs(source, vanilla_tags_source):
    stubs = goal11a_stubs(source, [(source / PUMPJACK_BE).read_text(encoding="utf-8")], vanilla_tags_source)
    name = "com/hbm/blockentity/NtmBlockEntityTypes.java"
    old = "MACHINE_OIL_WELL=new Ref()"
    if stubs[name].count(old) != 1:
        raise SystemExit(f"Goal19A cog/pumpjack stub anchor missing in {name}: {old}")
    stubs[name] = stubs[name].replace(old, old + ",MACHINE_PUMPJACK=new Ref()")
    # getConPos turns the facing with getCounterClockWise(Axis.Y); like the world's getClockWise(Axis), only Y is modelled.
    name = "net/minecraft/core/Direction.java"
    old = "public Direction getClockWise(Axis a){"
    if stubs[name].count(old) != 1:
        raise SystemExit(f"Goal19A cog/pumpjack stub anchor missing in {name}: {old}")
    stubs[name] = stubs[name].replace(
        old, "public Direction getCounterClockWise(Axis a){if(a!=Axis.Y)throw new UnsupportedOperationException();return getCounterClockWise();}" + old)
    return stubs
