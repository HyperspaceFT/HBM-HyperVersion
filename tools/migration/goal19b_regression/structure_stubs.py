"""Goal19B structure world: the actual industrial turbine block/BE geometry, port, lever and ownership bodies over the Goal18A world.

Extends goal18a_regression.structure_stubs.build_world (14B root, which extracts the production DummyableBlock
findCore/setPlacedBy/checkRequirement/fillSpace/makeExtra/onRemove, playerWillDestroy and MultiblockHandlerXR) without modifying it.
Added production bodies: MachineIndustrialTurbineBlock getDimensions/getOffset/newBlockEntity/fillSpace/useWithoutItem,
MachineIndustrialTurbineBlockEntity getConPos/getPowerPos, DummyableBlock neighborChanged/destroyIfOrphan (the turbine overrides neither
onRemove nor playerWillDestroy, so teardown is the inherited generic path: onRemove chain removal plus the orphan cascade).
Every other addition is a declared, anchored engine service (see SERVICES). Not Minecraft; no registry, codec, tick, render or audio code.
"""
from goal18a_regression.structure_stubs import build_world as base_world, SOURCE_PATHS as BASE_PATHS
from review_fixes.block_stubs import method

BLOCK = 'com/hbm/blocks/machine/MachineIndustrialTurbineBlock.java'
BE = 'com/hbm/blockentity/machine/MachineIndustrialTurbineBlockEntity.java'
SOURCE_PATHS = tuple(dict.fromkeys((*BASE_PATHS, BLOCK, BE)))

BLOCK_SIGNATURES = ('public BlockEntity newBlockEntity(', 'public int[] getDimensions(', 'public int getOffset(',
                    'protected InteractionResult useWithoutItem(', 'protected void fillSpace(')
BE_SIGNATURES = ('public DirPos[] getConPos(', 'public DirPos[] getPowerPos(')
DUMMY_SIGNATURES = ('public void neighborChanged(', 'private void destroyIfOrphan(')

# Declared engine-service stand-ins that carry the name of a production/engine class; none of them is a body under test.
SERVICES = ('Component', 'ChatFormatting', 'SoundSource', 'SoundEvent', 'SoundHolder', 'NtmSoundEvents', 'SoundUtils', 'PlayedSound',
            'InteractionResult', 'BlockHitResult')
# Shells whose production method bodies are extracted verbatim.
SHELLS = {'IndustrialTurbine': BLOCK, 'MachineIndustrialTurbineBlockEntity': BE}

ADDITIONS = r'''
enum SoundSource{BLOCKS,MASTER}
enum ChatFormatting{RED,GREEN,WHITE}
class SoundEvent{final String id;SoundEvent(String i){id=i;}}
class SoundHolder{private final SoundEvent event;SoundHolder(String i){event=new SoundEvent(i);}SoundEvent get(){return event;}}
class NtmSoundEvents{static final SoundHolder TURBINE_LEVER=new SoundHolder("block.chungus_lever");static final SoundHolder TURBINE_LARGE_LOOP=new SoundHolder("block.large_turbine_running");}
record PlayedSound(Vec3 pos,SoundEvent event,SoundSource source,float volume,float pitch){}
class SoundUtils{static void playAtVec3(Level level,Vec3 pos,SoundEvent event,SoundSource source,float volume,float pitch){level.sounds.add(new PlayedSound(pos,event,source,volume,pitch));}}
class Component{final String key;final List<ChatFormatting> styles=new ArrayList<>();private Component(String k){key=k;}
 static Component translatable(String k){return new Component(k);} Component withStyle(ChatFormatting f){styles.add(f);return this;}}
class InteractionResult{final String name;private InteractionResult(String n){name=n;}
 static final InteractionResult SUCCESS=new InteractionResult("SUCCESS"),CONSUME=new InteractionResult("CONSUME"),PASS=new InteractionResult("PASS"),FAIL=new InteractionResult("FAIL");
 static InteractionResult sidedSuccess(boolean isClientSide){return isClientSide?SUCCESS:CONSUME;}public String toString(){return name;}}
class BlockHitResult{}
class IndustrialTurbine extends DummyableBlock{__BLOCK__}
class MachineIndustrialTurbineBlockEntity extends BlockEntity{
 final BlockPos pos;final BlockState state;boolean operational;int leverPulls;
 MachineIndustrialTurbineBlockEntity(BlockPos p,BlockState s){pos=p;state=s;}
 BlockPos getBlockPos(){return pos;} BlockState getBlockState(){return state;} void onLeverPull(){leverPulls++;}
 __BE__}
'''

def swap(world, old, new):
    """One declared, anchored stand-in edit; a missing or ambiguous anchor fails the run."""
    if world.count(old) != 1: raise SystemExit(f'Stand-in anchor matched {world.count(old)} times: {old[:80]}')
    return world.replace(old, new, 1)

def build_world(source):
    world = swap(base_world(source), 'package goal18a;', 'package goal19b;')
    # Level: recorded sound plays, a block-entity map the fixture fills from the production newBlockEntity, the chunk-border query of
    # destroyIfOrphan, and the flag-1 neighbour update that Level.setBlock(flags 3) sends after the old state's onRemove.
    world = swap(world, 'boolean isClientSide; final Map<BlockPos,BlockState> states=new HashMap<>();',
                 'boolean isClientSide; final Map<BlockPos,BlockState> states=new HashMap<>(); final List<PlayedSound> sounds=new ArrayList<>(); final Map<BlockPos,BlockEntity> blockEntities=new HashMap<>(); boolean chunksLoaded=true; boolean notifyNeighbors=true; boolean hasChunksAt(BlockPos a,BlockPos b){return chunksLoaded;}')
    world = swap(world, 'BlockEntity getBlockEntity(BlockPos p){return inventories.contains(p)?new BlockEntity():null;}',
                 'BlockEntity getBlockEntity(BlockPos p){return blockEntities.containsKey(p)?blockEntities.get(p):inventories.contains(p)?new BlockEntity():null;}')
    world = swap(world, 'if(old.getBlock()!=s.getBlock())old.getBlock().onRemove(old,this,p,s,false);}',
                 'if(old.getBlock()!=s.getBlock())old.getBlock().onRemove(old,this,p,s,false);'
                 'if(notifyNeighbors)for(Direction d:Direction.values()){BlockPos np=p.relative(d);BlockState ns=getBlockState(np);if(!ns.isAir())ns.getBlock().neighborChanged(ns,this,np,s.getBlock(),p,false);}}')
    world = swap(world, ' Direction getOpposite(){return values()[ordinal()^1];}',
                 ' Direction getOpposite(){return values()[ordinal()^1];} int getStepX(){return dx;} int getStepY(){return dy;} int getStepZ(){return dz;}')
    world = swap(world, 'class Vec3{final double x,y,z;', 'class Vec3{static Vec3 atCenterOf(BlockPos p){return new Vec3(p.x()+0.5,p.y()+0.5,p.z()+0.5);}final double x,y,z;')
    world = swap(world, 'class Player extends LivingEntity {ItemStack getMainHandItem(){return new ItemStack(1);}',
                 'class Player extends LivingEntity {final List<Component> messages=new ArrayList<>(); void sendSystemMessage(Component c){messages.add(c);} ItemStack getMainHandItem(){return new ItemStack(1);}')
    world = swap(world, ' void setPlacedBy(Level l,BlockPos p,BlockState s,LivingEntity pl,ItemStack st){}',
                 ' void setPlacedBy(Level l,BlockPos p,BlockState s,LivingEntity pl,ItemStack st){} void neighborChanged(BlockState s,Level l,BlockPos p,Block b,BlockPos from,boolean moving){}')
    dummy = (source / 'com/hbm/blocks/DummyableBlock.java').read_text(encoding='utf-8')
    world = swap(world, 'class DummyableBlock extends Block {', 'class DummyableBlock extends Block {' + '\n'.join(method(dummy, s) for s in DUMMY_SIGNATURES))
    block = (source / BLOCK).read_text(encoding='utf-8')
    be = (source / BE).read_text(encoding='utf-8')
    additions = (ADDITIONS.replace('__BLOCK__', '\n'.join(method(block, s) for s in BLOCK_SIGNATURES))
                 .replace('__BE__', '\n'.join(method(be, s) for s in BE_SIGNATURES)))
    return world + additions
