package com.hbm.blockentity.machine;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.blocks.DummyableBlock;
import net.minecraft.core.*;
import net.minecraft.world.entity.*;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.*;
import java.util.*;

/** Actual BE calls over instrumented entities, not vanilla damage or motion acceptance. */
public class Goal17BEntityRegression extends Goal17BMachineRegression {
    static final Direction[] FACINGS={Direction.NORTH,Direction.SOUTH,Direction.EAST,Direction.WEST};
    static Direction axis(Direction f){return switch(f){case NORTH->Direction.EAST;case EAST->Direction.SOUTH;case SOUTH->Direction.WEST;case WEST->Direction.NORTH;default->throw new AssertionError();};}
    static void box(AABB actual,BlockPos p,Direction f,double low,double high){
        Direction d=axis(f);double x=p.getX()+.5,z=p.getZ()+.5;
        double ax=x+d.getStepX()*low,bx=x+d.getStepX()*high,az=z+d.getStepZ()*low,bz=z+d.getStepZ()*high;
        check(actual.minX==Math.min(ax,bx)-(d.getStepX()==0?1.5:0)&&actual.maxX==Math.max(ax,bx)+(d.getStepX()==0?1.5:0)&&actual.minZ==Math.min(az,bz)-(d.getStepZ()==0?1.5:0)&&actual.maxZ==Math.max(az,bz)+(d.getStepZ()==0?1.5:0)&&actual.minY==p.getY()&&actual.maxY==p.getY()+3,"original independent AABB "+f+" "+low+"/"+high);
    }
    static <T extends Entity> T at(T e,Direction facing,double offset){
        Direction d=axis(facing);e.setPos(.5+d.getStepX()*offset,1,.5+d.getStepZ()*offset);return e;
    }
    static void pushed(Entity e,Direction f){
        Direction d=axis(f);check(Math.abs(e.getDeltaMovement().x+d.getStepX()*.2)<1e-9&&Math.abs(e.getDeltaMovement().z+d.getStepZ()*.2)<1e-9,"axis .2 push "+f);
    }
    public static void main(String[] args){
        for(Direction f:FACINGS){
            scenario();BlockPos p=new BlockPos(10,30,-20);
            box(MachineTurbofanBlockEntity.getExhaustBox(p,f),p,f,-19.5,-3.5);box(MachineTurbofanBlockEntity.getIntakeBox(p,f),p,f,3.5,8.5);box(MachineTurbofanBlockEntity.getBlenderBox(p,f),p,f,3.5,3.75);
            Level l=fresh();var b=turbine(l,0,f,1,Fluids.KEROSENE,10);
            Entity exhaust=at(new Entity(),f,-5),intake=at(new Entity(),f,5),outside=at(new Entity(),f,9),nonliving=at(new Entity(),f,3.6);
            LivingEntity living=at(new LivingEntity(),f,3.6);Player player=at(player(l),f,-6);
            l.testEntities.addAll(List.of(exhaust,intake,outside,nonliving,living,player));step(l,b);
            pushed(exhaust,f);pushed(intake,f);pushed(living,f);check(!player.hurtMarked&&player.getDeltaMovement().equals(Vec3.ZERO),"server player neither pushed nor hurtMarked (17B P2: client pushes the local player)");
            check(exhaust.fireSeconds==5&&exhaust.damageAmounts.equals(List.of(5F)),"afterburn exhaust fire5sec damage5");
            check(intake.fireSeconds==0&&intake.damageAmounts.isEmpty(),"intake only pull");
            check(outside.getDeltaMovement().equals(Vec3.ZERO)&&outside.damageAmounts.isEmpty(),"outside range untouched");
            check(living.damageAmounts.equals(List.of(1000F))&&living.slowCalls==1&&living.effects.equals(List.of("hurt","slow")),"blender hurt then modern web call");
            check(living.damageKinds.equals(List.of("hbmsntm:turbofan")),"real custom damage selection");
            check(!nonliving.isAlive()&&!living.isAlive()&&b.blood.getFill()==50&&b.showBlood,"dead living only blood50");
            check(l.queries.size()==3,"three actual production queries");
            scenario();l=fresh();b=turbine(l,0,f,0,Fluids.KEROSENE,10);exhaust=at(new Entity(),f,-5);l.testEntities.add(exhaust);step(l,b);pushed(exhaust,f);
            check(exhaust.fireSeconds==0&&exhaust.damageAmounts.isEmpty(),"A0 exhaust no fire/damage");
            scenario();l=fresh();b=turbine(l,0,f,3,Fluids.KEROSENE,10);living=at(new LivingEntity(),f,3.6);living.acceptDamage=false;l.testEntities.add(living);step(l,b);
            check(living.isAlive()&&living.slowCalls==1&&b.blood.getFill()==0,"hurt false live no blood without bypass");
            scenario();l=fresh();b=turbine(l,0,f,3,Fluids.KEROSENE,10);living=at(new LivingEntity(),f,3.6);living.acceptDamage=false;living.health=0;l.testEntities.add(living);b.blood.setFill(23990);step(l,b);
            check(b.blood.getFill()==24000&&b.showBlood,"post-hit predicate includes already dead hurt false, cap24000");
            for(int mode=0;mode<4;mode++){
                scenario();l=fresh();b=turbine(l,0,f,3,mode==2?Fluids.WATER:Fluids.KEROSENE,mode==1?0:10);living=at(new LivingEntity(),f,3.6);l.testEntities.add(living);
                if(mode==0)l.powered.add(b.getConPos()[0].makeCompat());if(mode==3)l.isClientSide=true;step(l,b);
                check(living.damageAmounts.isEmpty()&&living.slowCalls==0&&living.getDeltaMovement().equals(Vec3.ZERO)&&b.blood.getFill()==0,"stopped/empty/nonAERO/client no hazard mode"+mode);
            }
        }

        for(Direction f:FACINGS)for(int mode=0;mode<10;mode++){
            scenario();Level l=fresh();l.isClientSide=true;var b=turbine(l,0,f,3,mode==6?Fluids.WATER:Fluids.KEROSENE,10);
            b.wasOn=mode!=4;b.consumption=mode==5?0:4;b.afterburner=3;b.redstonePowered=mode==3;
            Player local=at(player(l),f,mode==7?5:mode==9?-5:3.6);local.creative=mode==2;if(mode==1)local.world=new Level();
            com.hbm.main.NuclearTechMod.proxy.player=mode==8?null:local;
            Vec3 motion=new Vec3(1,2,3);local.setDeltaMovement(motion);step(l,b);
            check(local.slowCalls==(mode==0?1:0),"localclient web gates mode"+mode+"/"+f);
            Direction d=axis(f);boolean push=mode==0||mode==7||mode==9;
            check(push?local.getDeltaMovement().equals(motion.add(-d.getStepX()*.2,0,-d.getStepZ()*.2)):local.getDeltaMovement()==motion,mode==9?"17B P2: client pushes the gated local player exactly once in the exhaust box mode"+mode+"/"+f:"17B P2: client pushes the gated local player exactly once (intake box, not exhaust), else motion untouched mode"+mode+"/"+f);
            check(local.damageAmounts.isEmpty()&&local.fireSeconds==0&&!local.hurtMarked&&b.blood.getFill()==0&&b.tank.getFill()==10&&b.power==0,"client only local web/push, no damage/state");
        }
        com.hbm.main.NuclearTechMod.proxy.player=null;

        System.out.println("Goal17B entities: "+checks+" assertions; "+scenarios+" independent scenarios; "+executedTicks+" executed ticks");
    }
}
