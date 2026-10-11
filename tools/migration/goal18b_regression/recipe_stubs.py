"""Goal18B recipe world: the Goal18A recipe world unchanged. Goal18B only appends default rows to the production
CrystallizerRecipes, so the same production sources (CrystallizerRecipes, sync, client sync, packet, JEI handler, loader base
and AssemblyMachineRecipes) compile over the same stand-ins; the JEI bridge stand-in keeps its Goal18A name goal18a.JeiBridge."""
from goal18a_regression.recipe_stubs import recipe_stubs, RECIPE_SOURCES, EXTRA

__all__ = ('recipe_stubs', 'RECIPE_SOURCES', 'EXTRA')
