"""Goal14C production-method extraction using the existing bounded 14B world.

Only Minecraft services are stand-ins. Compressor dimensions, placement, port
positions, proxy roles and ownership/teardown bodies are copied from production.
"""
from pathlib import Path
from goal14b_regression.structure_stubs import build_world as base_world
from review_fixes.block_stubs import method


def build_world(source: Path):
    world = base_world(source).replace("package goal14b;", "package goal14c;")
    world = world.replace("Direction getOpposite(){", "Direction getClockWise(){return switch(this){case NORTH->EAST;case EAST->SOUTH;case SOUTH->WEST;case WEST->NORTH;default->this;};} Direction getOpposite(){")
    world = world.replace("record DirPos(BlockPos pos){BlockPos makeCompat(){return pos;}}", "record DirPos(BlockPos pos,Direction dir){DirPos(BlockPos p){this(p,Direction.NORTH);} BlockPos makeCompat(){return pos;} Direction getDir(){return dir;}}")
    world = world.replace("class Block {", "class BlockEntity{} class ProxyComboBlockEntity extends BlockEntity {boolean fluid,power;ProxyComboBlockEntity(BlockPos p,BlockState s){} ProxyComboBlockEntity fluid(){fluid=true;return this;} ProxyComboBlockEntity power(){power=true;return this;}} class Block {")
    world = world.replace("BlockState defaultBlockState(){", "BlockEntity newBlockEntity(BlockPos p,BlockState s){return null;} BlockState defaultBlockState(){")
    block = (source / "com/hbm/blocks/machine/MachineCompressorBlock.java").read_text(encoding="utf-8")
    signatures = ("public int[] getDimensions(", "public int getOffset(", "public int[][] getAllDimensions(",
                  "public BlockEntity newBlockEntity(", "protected boolean checkRequirement(", "protected void fillSpace(",
                  "public BlockState playerWillDestroy(", "public void onRemove(", "private void destroyCompressor(", "private BlockPos findOwnedCore(")
    bodies = "\n".join(method(block, signature) for signature in signatures)
    be = (source / "com/hbm/blockentity/machine/MachineCompressorBlockEntity.java").read_text(encoding="utf-8")
    ports = method(be, "public static DirPos[] getPortProxies(")
    return world + "\nclass Compressor extends DummyableBlock {" + bodies + "}\nclass MachineCompressorBlockEntity extends BlockEntity {MachineCompressorBlockEntity(BlockPos p,BlockState s){}" + ports + "}\n"
