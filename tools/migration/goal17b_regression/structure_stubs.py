"""Actual turbofan geometry/ownership methods over existing declared engine/drop services."""
from goal16b_regression.structure_stubs import build_world as base_world
from review_fixes.block_stubs import method

SOURCE_PATHS=('com/hbm/blocks/DummyableBlock.java','com/hbm/handler/MultiblockHandlerXR.java',
 'com/hbm/blocks/machine/MachineTurbofanBlock.java','com/hbm/blockentity/machine/MachineTurbofanBlockEntity.java',
 'com/hbm/blocks/machine/MachineCompressorBlock.java','com/hbm/blockentity/machine/MachineCompressorBlockEntity.java',
 'com/hbm/blocks/machine/MachineFractionTowerBlock.java','com/hbm/blocks/machine/FractionSpacerBlock.java',
 'com/hbm/blocks/generic/SteelBeamBlock.java','com/hbm/blocks/generic/SteelGrateBlock.java',
 'com/hbm/blocks/machine/MachineCokerBlock.java','com/hbm/blockentity/machine/oil/MachineCokerBlockEntity.java',
 'com/hbm/blocks/machine/MachineMixerBlock.java','com/hbm/blocks/machine/MachineCentrifugeBlock.java')

def build_world(source):
    world=base_world(source).replace('package goal16b;','package goal17b;')
    world=world.replace('s.getBlock() instanceof Mixer || s.getBlock() instanceof Centrifuge',
                        's.getBlock() instanceof Mixer || s.getBlock() instanceof Centrifuge || s.getBlock() instanceof Turbofan')
    block=(source/'com/hbm/blocks/machine/MachineTurbofanBlock.java').read_text(encoding='utf-8')
    signatures=('public int[] getDimensions(','public int getOffset(','public int[][] getAllDimensions(',
     'public BlockEntity newBlockEntity(','protected boolean checkRequirement(','protected void fillSpace(',
     'public BlockState playerWillDestroy(','public void onRemove(','private void destroyTurbofan(','private BlockPos findOwnedCore(')
    bodies='\n'.join(method(block,s) for s in signatures)
    be=(source/'com/hbm/blockentity/machine/MachineTurbofanBlockEntity.java').read_text(encoding='utf-8')
    ports='\n'.join(method(be,s) for s in ('public static Direction getIntakeDirection(','public static DirPos[] getPortProxies('))
    return world+'\nclass Turbofan extends DummyableBlock{'+bodies+'}\nclass MachineTurbofanBlockEntity extends BlockEntity{MachineTurbofanBlockEntity(BlockPos p,BlockState s){}'+ports+'}\n'
