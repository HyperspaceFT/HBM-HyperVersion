"""Actual four-cell ownership methods over declared engine/drop services, no Minecraft launch."""
from goal16a_regression.structure_stubs import build_world as base_world
from review_fixes.block_stubs import method


def build_world(source):
    world = base_world(source).replace('package goal16a;', 'package goal16b;')
    world = world.replace('s.getBlock() instanceof Mixer &&', '(s.getBlock() instanceof Mixer || s.getBlock() instanceof Centrifuge) &&')
    # Exercise the actual inherited player drop callback; loot creation remains a recorded engine service.
    inherited = method((source / 'com/hbm/blocks/DummyableBlock.java').read_text(encoding='utf-8'), 'public BlockState playerWillDestroy(')
    world = world.replace('class DummyableBlock extends Block {', 'class DummyableBlock extends Block {' + inherited)
    world = world.replace('class Block {', 'class Block {static void dropResources(BlockState s,Level l,BlockPos p,BlockEntity be,Player player,ItemStack tool){l.drops++;}')
    world = world.replace('class Player extends LivingEntity {', 'class Player extends LivingEntity {ItemStack getMainHandItem(){return new ItemStack(1);}')
    world = world.replace('public BlockState getBlockState(BlockPos p){', 'BlockEntity getBlockEntity(BlockPos p){return inventories.contains(p)?new BlockEntity():null;}public BlockState getBlockState(BlockPos p){')
    block = (source / 'com/hbm/blocks/machine/MachineCentrifugeBlock.java').read_text(encoding='utf-8')
    signatures = ('public int[] getDimensions(', 'public int getOffset(', 'public BlockEntity newBlockEntity(',
                  'public BlockState playerWillDestroy(', 'public void onRemove(',
                  'private void destroyCentrifuge(', 'private BlockPos findOwnedCore(')
    bodies = '\n'.join(method(block, s) for s in signatures)
    return world + '\nclass Centrifuge extends DummyableBlock{' + bodies + '}\nclass MachineCentrifugeBlockEntity extends BlockEntity{MachineCentrifugeBlockEntity(BlockPos p,BlockState s){}}\n'
