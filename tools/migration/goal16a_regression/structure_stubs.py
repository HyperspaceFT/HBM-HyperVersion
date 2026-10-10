"""Selected actual placement/ownership bodies; declared engine and loot services."""
from goal15b_regression.structure_stubs import build_world as base_world
from review_fixes.block_stubs import method


def build_world(source):
    world = base_world(source).replace('package goal15b;', 'package goal16a;')
    # Engine inventory destruction service: one core-held inventory, drained exactly once.
    world = world.replace('int drops,scheduled;', 'int drops,scheduled,inventoryDrops; final Set<BlockPos> inventories=new HashSet<>();')
    world = world.replace('states.put(p,s);if(old.getBlock()', 'states.put(p,s);if(s.getBlock() instanceof Mixer && s.getValue(DummyableBlock.TYPE)==DummyBlockType.CORE)inventories.add(p);if(old.getBlock()')
    world = world.replace('static void dropContentsOnDestroy(BlockState a,BlockState b,Level l,BlockPos p){}',
                          'static void dropContentsOnDestroy(BlockState a,BlockState b,Level l,BlockPos p){if(a.getBlock()!=b.getBlock()&&l.inventories.remove(p))l.inventoryDrops++;}')
    block = (source / 'com/hbm/blocks/machine/MachineMixerBlock.java').read_text(encoding='utf-8')
    signatures = ('public int[] getDimensions(', 'public int getOffset(', 'public BlockEntity newBlockEntity(',
                  'protected void fillSpace(', 'public BlockState playerWillDestroy(', 'public void onRemove(',
                  'private void destroyMixer(', 'private BlockPos findOwnedCore(')
    bodies = '\n'.join(method(block, s) for s in signatures)
    return world + '\nclass Mixer extends DummyableBlock{' + bodies + '}\nclass MachineMixerBlockEntity extends BlockEntity{MachineMixerBlockEntity(BlockPos p,BlockState s){}}\n'
