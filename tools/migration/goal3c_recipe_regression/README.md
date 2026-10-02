# Goal 3C recipe loader regression

Run `verify_goal3c_recipes.py` from the NEO repository root with the existing
Python runtime. It uses the cached JDK 21 and Gson JAR. Every run creates its
own `scratch-config/hbmRecipes` under `build/migration/goal3c/recipe-regression/`;
it does not read or write the player's recipe config.

The harness compiles the current production `SerializableRecipe`,
`GenericRecipes`, `GenericRecipe`, and `AssemblyMachineRecipes`. Minecraft,
registry, localization, fluid, and other recipe-family declarations are
peripheral stubs. It checks that the assembler singleton is registered once,
then filters the other recipe families so only assembler loading touches the
scratch config. The checks cover defaults and underscore template creation,
repeat initialization, edited underscore content, intentionally empty enabled
custom files, a changed enabled custom recipe, received-stream precedence,
and restoration of the local custom file after clearing that stream.

The checks also round-trip tag IDs and counts through the production generic
serializer/parser, including an omitted count of one, and verify the existing
item/count/meta format. The per-run
`ass-shredder-from-production-writer.json` is a schema-correct example of the
normal `ass.shredder` recipe as emitted by production code. Registry item IDs
are supplied by stubs that map the named NEO fields to their matching lowercase
IDs. The fixture's `ComparableStack(Item)` and `(Item, count)` constructors
match production's wildcard metadata value of `32767`; the example therefore
includes that value on the two-motor ingredient. The test verifies the
registered default, written JSON, and parsed custom entry all retain it. This
file is evidence for recipe schema and ingredient counts, not a packaged-game
resource.

`receiveRecipes` is called directly in this harness. It proves the helper's
priority over a local file; it does not prove that a multiplayer packet invokes
the helper. This check does not start Minecraft, dispatch login or reload
events, open screens, run an assembler, or test an actual client/server pair.

Goal 10A registers `CrucibleRecipes.INSTANCE` in `SerializableRecipe.registerAllHandlers` after
`ChemicalPlantRecipes`. The stand-in handler list therefore also declares a `CrucibleRecipes` singleton
(like the blast furnace and chemical plant ones); this suite still filters every handler except the
assembler, and its count is unchanged. The Goal 4 shredder and Goal 5B press suites inherit the
stand-in. `verify_goal10a.py` compiles the real `CrucibleRecipes` and checks its registration and
`hbmCrucible.json`.
