"""Extract engine geometry/lifecycle methods from production, with bounded engine services."""
from goal14c_regression.structure_stubs import build_world as base_world
from review_fixes.block_stubs import method

def build_world(source):
    world = base_world(source).replace('package goal14c;', 'package goal15a;')
    world = world.replace('Direction getClockWise(){','Direction getCounterClockWise(){return getClockWise().getOpposite();} Direction getClockWise(){')
    # Keep inherited unrelated shells; only the new Engine shell executes in the fixture.
    block = (source/'com/hbm/blocks/machine/MachineCombustionEngineBlock.java').read_text(encoding='utf-8')
    signatures = ('public int[] getDimensions(', 'public int getOffset(', 'public int[][] getAllDimensions(', 'protected boolean checkRequirement(',
                  'public BlockEntity newBlockEntity(', 'protected void fillSpace(',
                  'public BlockState playerWillDestroy(', 'public void onRemove(',
                  'private void destroyEngine(', 'private BlockPos findOwnedCore(')
    bodies = '\n'.join(method(block, signature) for signature in signatures)
    be = (source/'com/hbm/blockentity/machine/MachineCombustionEngineBlockEntity.java').read_text(encoding='utf-8')
    ports = method(be, 'public static DirPos[] getPortProxies(')
    return world + '\nclass Engine extends DummyableBlock {' + bodies + '}\nclass MachineCombustionEngineBlockEntity extends BlockEntity{MachineCombustionEngineBlockEntity(BlockPos p,BlockState s){}' + ports + '}\n'
