"""Production structure/ownership bodies; explicit engine services only."""
from goal14c_regression.structure_stubs import build_world as base_world
from review_fixes.block_stubs import method

def build_world(source):
    world=base_world(source).replace('package goal14c;','package goal15b;')
    world=world.replace('boolean fluid,power;','boolean fluid,power,inventory;').replace('ProxyComboBlockEntity fluid(){','ProxyComboBlockEntity inventory(){inventory=true;return this;} ProxyComboBlockEntity fluid(){')
    world=world.replace('public BlockState getBlockState(BlockPos p){','boolean isOutsideBuildHeight(BlockPos p){return p.y()<0||p.y()>=320;} public BlockState getBlockState(BlockPos p){')
    block=(source/'com/hbm/blocks/machine/MachineCokerBlock.java').read_text(encoding='utf-8')
    signatures=('public int[] getDimensions(','public int getOffset(','public int[][] getAllDimensions(','public Set<BlockPos> getStructurePositions(','public BlockEntity newBlockEntity(','protected boolean checkRequirement(','protected void fillSpace(','public BlockState playerWillDestroy(','public void onRemove(','private void destroyCoker(','private BlockPos findOwnedCore(')
    bodies='\n'.join(method(block,s) for s in signatures)
    be=(source/'com/hbm/blockentity/machine/oil/MachineCokerBlockEntity.java').read_text(encoding='utf-8')
    ports=method(be,'public static DirPos[] getPortProxies(')
    return world+'\nclass Coker extends DummyableBlock{'+bodies+'}\nclass MachineCokerBlockEntity extends BlockEntity{MachineCokerBlockEntity(BlockPos p,BlockState s){}'+ports+'}\n'
