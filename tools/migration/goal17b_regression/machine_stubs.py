"""Goal17B complete production machines with explicit bounded engine services."""
import re
from goal15a_regression.machine_stubs import machine_stubs as base_stubs, MACHINE_SOURCES as BASE
from goal11a_regression.stubs import pollution_handler, ft_polluting
from goal10b_regression.stubs import method_body

EXTRA = ('com/hbm/blockentity/machine/MachineTurbofanBlockEntity.java',
         'com/hbm/inventory/menus/MachineTurbofanMenu.java', 'com/hbm/inventory/recipes/anvil/AnvilSmithingIngotMoldRecipe.java', 'com/hbm/inventory/recipes/anvil/AnvilSmithingBladeMoldRecipe.java')
MACHINE_SOURCES = tuple(dict.fromkeys((*BASE, *EXTRA)))
EXTRACTED = ('com/hbm/inventory/fluid/Fluids.java','com/hbm/handler/pollution/PollutionHandler.java',
             'com/hbm/inventory/fluid/trait/FT_Polluting.java','com/hbm/lib/Library.java',
             'com/hbm/items/NtmItems.java','com/hbm/blockentity/LoadedBaseBlockEntity.java',
             'com/hbm/registry/NtmDamageTypes.java','com/hbm/blocks/DummyableBlock.java',
             'com/hbm/items/component/NtmDataComponents.java','com/hbm/util/TagsUtil.java')

def insert(stubs,path,anchor,text):
    if anchor not in stubs[path]: raise SystemExit(f'Goal17B service anchor missing: {path}: {anchor}')
    stubs[path]=stubs[path].replace(anchor,anchor+text,1)

def machine_stubs(source,extras,tags,jar):
    stubs=base_stubs(source,[(source/p).read_text(encoding='utf-8') for p in EXTRA]+extras,tags,jar)
    stubs['com/hbm/handler/pollution/PollutionHandler.java']=pollution_handler(source)
    stubs['com/hbm/inventory/fluid/trait/FT_Polluting.java']=ft_polluting(source)
    text=(source/'com/hbm/inventory/fluid/Fluids.java').read_text(encoding='utf-8')
    floats=dict(re.findall(r'public static final float ((?:SOOT|POISON|LEAD)_[A-Z_]+) = ([^;]+);',text))
    statements=[]
    for name in ('KEROSENE','DIESEL'):
        definition=re.search(r'^\s*'+name+r' =\s+new FluidType\([^;]+;',text,re.M)
        traits=re.findall(r'\b(P_[A-Z_]+)\b',definition.group()) if definition else []
        if len(traits)!=1: raise SystemExit('Missing real pollution declaration: '+name)
        chain=re.search(r'public static final FT_Polluting '+traits[0]+r' =\s+new FT_Polluting\(\)([^;]+);',text).group(1)
        for key,value in floats.items():
            chain=re.sub(r'\b'+key+r'\b','('+value.replace('PollutionHandler.','com.hbm.handler.pollution.PollutionHandler.')+')',chain)
        chain=chain.replace('PollutionType.','com.hbm.handler.pollution.PollutionHandler.PollutionType.')
        statements.append(f'{name}.addTraits(new com.hbm.inventory.fluid.trait.FT_Polluting(){chain});')
    insert(stubs,'com/hbm/inventory/fluid/Fluids.java','public class Fluids{',
           'public static void initializeGoal17BFuels(){initializeGoal14CFuels();'+''.join(statements)+'}')
    insert(stubs,'com/hbm/blockentity/LoadedBaseBlockEntity.java','public int dirty,packs;',
           method_body((source/'com/hbm/blockentity/LoadedBaseBlockEntity.java').read_text(encoding='utf-8'),'public void onChunkUnloaded()','LoadedBaseBlockEntity'))
    stubs['net/minecraft/world/phys/AABB.java']='''package net.minecraft.world.phys;
public class AABB{public final double minX,minY,minZ,maxX,maxY,maxZ,a,b,c,d,e,f;
public AABB(double x,double y,double z,double xx,double yy,double zz){minX=a=Math.min(x,xx);minY=b=Math.min(y,yy);minZ=c=Math.min(z,zz);maxX=d=Math.max(x,xx);maxY=e=Math.max(y,yy);maxZ=f=Math.max(z,zz);}
public AABB(net.minecraft.core.BlockPos p){this(p.getX(),p.getY(),p.getZ(),p.getX()+1,p.getY()+1,p.getZ()+1);}
public AABB move(double x,double y,double z){return new AABB(a+x,b+y,c+z,d+x,e+y,f+z);}public AABB inflate(double n){return new AABB(a-n,b-n,c-n,d+n,e+n,f+n);}
public boolean intersects(AABB q){return a<q.d&&d>q.a&&b<q.e&&e>q.b&&c<q.f&&f>q.c;}}'''
    insert(stubs,'net/minecraft/world/entity/Entity.java','public class Entity{','''
public boolean hurtMarked;public int fireSeconds,slowCalls;public boolean acceptDamage=true;
public final java.util.List<Float> damageAmounts=new java.util.ArrayList<>();public final java.util.List<Object> damageKinds=new java.util.ArrayList<>();public final java.util.List<String> effects=new java.util.ArrayList<>();
public void igniteForSeconds(float n){fireSeconds=(int)n;effects.add("fire");}public void setSecondsOnFire(int n){igniteForSeconds(n);}
public void makeStuckInBlock(net.minecraft.world.level.block.state.BlockState s,net.minecraft.world.phys.Vec3 v){slowCalls++;effects.add("slow");}
public net.minecraft.world.phys.AABB getBoundingBox(){return new net.minecraft.world.phys.AABB(getX()-.01,getY(),getZ()-.01,getX()+.01,getY()+.02,getZ()+.01);}
''')
    anchor='public boolean hurt(DamageSource s,float amount){return false;}'
    if anchor not in stubs['net/minecraft/world/entity/Entity.java']: raise SystemExit('Entity service anchor changed')
    stubs['net/minecraft/world/entity/Entity.java']=stubs['net/minecraft/world/entity/Entity.java'].replace(anchor,
        'public boolean hurt(DamageSource s,float amount){damageAmounts.add(amount);damageKinds.add(s.type());effects.add("hurt");if(acceptDamage)health-=amount;return acceptDamage;}')
    insert(stubs,'net/minecraft/world/level/Level.java','public class Level implements BlockGetter{','''
public final java.util.List<net.minecraft.world.entity.Entity> testEntities=new java.util.ArrayList<>();public final java.util.List<net.minecraft.world.phys.AABB> queries=new java.util.ArrayList<>();
public java.util.List<net.minecraft.world.entity.Entity> getEntities(net.minecraft.world.entity.Entity except,net.minecraft.world.phys.AABB box){queries.add(box);return testEntities.stream().filter(e->e!=except&&e.getBoundingBox().intersects(box)).toList();}
public <T extends net.minecraft.world.entity.Entity> java.util.List<T> getEntitiesOfClass(Class<T> type,net.minecraft.world.phys.AABB box){queries.add(box);return testEntities.stream().filter(e->type.isInstance(e)&&e.getBoundingBox().intersects(box)).map(type::cast).toList();}
public net.minecraft.world.damagesource.DamageSources damageSources(){return new net.minecraft.world.damagesource.DamageSources();}
''')
    insert(stubs,'net/minecraft/world/damagesource/DamageSources.java','public class DamageSources{','public DamageSource onFire(){return new DamageSource("minecraft:on_fire");}')
    damage=(source/'com/hbm/registry/NtmDamageTypes.java').read_text(encoding='utf-8')
    if not re.search(r'\bTURBOFAN\s*=',damage): raise SystemExit('Real TURBOFAN key missing')
    insert(stubs,'com/hbm/registry/NtmDamageTypes.java','public class NtmDamageTypes{','public static final Object TURBOFAN="hbmsntm:turbofan";')

    insert(stubs,'net/minecraft/world/level/Level.java','public class Level implements BlockGetter{',
           'public boolean hasChunkAt(net.minecraft.core.BlockPos p){return true;}')
    insert(stubs,'net/minecraft/world/level/Level.java','public class Level implements BlockGetter{',
           'public <T extends net.minecraft.world.entity.Entity> java.util.List<T> getEntitiesOfClass(Class<T> type,net.minecraft.world.phys.AABB box,java.util.function.Predicate<? super T> filter){return getEntitiesOfClass(type,box).stream().filter(filter).toList();}')
    insert(stubs,'net/minecraft/server/level/ServerLevel.java','public class ServerLevel extends net.minecraft.world.level.Level{',
           'public net.minecraft.server.MinecraftServer getServer(){return new net.minecraft.server.MinecraftServer(java.util.List.of(this));}')
    insert(stubs,'net/minecraft/server/MinecraftServer.java','public class MinecraftServer{',
           'public PlayerList getPlayerList(){return new PlayerList();}public static class PlayerList{public void broadcast(Object... args){}}')
    stubs['net/minecraft/network/protocol/game/ClientboundLevelParticlesPacket.java']='package net.minecraft.network.protocol.game;public class ClientboundLevelParticlesPacket{public ClientboundLevelParticlesPacket(Object particle,boolean force,double x,double y,double z,float dx,float dy,float dz,float speed,int count){}}'
    insert(stubs,'com/hbm/particle/NtmParticleTypes.java','public class NtmParticleTypes{',
           'public static final Ref GAS_FLAME=new Ref("gas_flame");')


    n='net/minecraft/world/level/Level.java'
    stubs[n]=stubs[n].replace('public <T> List<T> getEntitiesOfClass(Class<T> c,net.minecraft.world.phys.AABB box){return new ArrayList<>();}','')
    n='net/minecraft/tags/ItemTags.java'
    stubs[n]=stubs[n].replace('public static Object create(net.minecraft.resources.ResourceLocation id){return id.n()+":"+id.p();}','public static net.minecraft.tags.TagKey<net.minecraft.world.item.Item> create(net.minecraft.resources.ResourceLocation id){return net.minecraft.tags.TagKey.create(null,id);}')
    provider=(source/'com/hbm/blockentity/IUpgradeInfoProvider.java').read_text(encoding='utf-8')
    efficiency=re.search(r'String KEY_EFFICIENCY = "[^"]+";',provider).group()
    insert(stubs,'com/hbm/blockentity/IUpgradeInfoProvider.java','public interface IUpgradeInfoProvider{',efficiency)

    n='net/minecraft/world/entity/player/Player.java'
    stubs[n]=stubs[n].replace('public double getX(){return 0;}','public double getX(){return super.getX();}').replace('public double getY(){return 0;}','public double getY(){return super.getY();}').replace('public double getZ(){return 0;}','public double getZ(){return super.getZ();}')
    insert(stubs,n,'public class Player extends LivingEntity{','public boolean isCreative(){return creative;}')

    for path in MACHINE_SOURCES: stubs.pop(path,None)
    return stubs
