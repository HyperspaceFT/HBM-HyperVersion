"""Actual crystallizer geometry/ownership methods over the inherited declared engine/drop services."""
from goal17b_regression.structure_stubs import build_world as base_world
from review_fixes.block_stubs import method

SOURCE_PATHS = ('com/hbm/blocks/DummyableBlock.java', 'com/hbm/handler/MultiblockHandlerXR.java',
                'com/hbm/blocks/machine/MachineCrystallizerBlock.java', 'com/hbm/blockentity/machine/MachineCrystallizerBlockEntity.java',
                'com/hbm/blocks/machine/MachineTurbofanBlock.java', 'com/hbm/blockentity/machine/MachineTurbofanBlockEntity.java',
                'com/hbm/blocks/machine/MachineCompressorBlock.java', 'com/hbm/blockentity/machine/MachineCompressorBlockEntity.java',
                'com/hbm/blocks/machine/MachineFractionTowerBlock.java', 'com/hbm/blocks/machine/FractionSpacerBlock.java',
                'com/hbm/blocks/generic/SteelBeamBlock.java', 'com/hbm/blocks/generic/SteelGrateBlock.java',
                'com/hbm/blocks/machine/MachineCokerBlock.java', 'com/hbm/blockentity/machine/oil/MachineCokerBlockEntity.java',
                'com/hbm/blocks/machine/MachineMixerBlock.java', 'com/hbm/blocks/machine/MachineCentrifugeBlock.java')

def build_world(source):
    world = base_world(source).replace('package goal17b;', 'package goal18a;')
    world = world.replace('s.getBlock() instanceof Mixer || s.getBlock() instanceof Centrifuge || s.getBlock() instanceof Turbofan',
                          's.getBlock() instanceof Mixer || s.getBlock() instanceof Centrifuge || s.getBlock() instanceof Turbofan || s.getBlock() instanceof Crystallizer')
    block = (source / 'com/hbm/blocks/machine/MachineCrystallizerBlock.java').read_text(encoding='utf-8')
    signatures = ('public int[] getDimensions(', 'public int getOffset(', 'public BlockEntity newBlockEntity(',
                  'protected boolean checkRequirement(', 'protected void fillSpace(', 'public BlockState playerWillDestroy(',
                  'public void onRemove(', 'private void destroyCrystallizer(', 'private BlockPos findOwnedCore(')
    bodies = '\n'.join(method(block, s) for s in signatures)
    be = (source / 'com/hbm/blockentity/machine/MachineCrystallizerBlockEntity.java').read_text(encoding='utf-8')
    statics = '\n'.join(method(be, s) for s in ('public static Direction getLadderSide(', 'public static BlockPos[] getCornerProxies(', 'public static DirPos[] getConnectionPositions('))
    return world + '\nclass Crystallizer extends DummyableBlock{' + bodies + '}\nclass MachineCrystallizerBlockEntity extends BlockEntity{MachineCrystallizerBlockEntity(BlockPos p,BlockState s){}' + statics + '}\n'
