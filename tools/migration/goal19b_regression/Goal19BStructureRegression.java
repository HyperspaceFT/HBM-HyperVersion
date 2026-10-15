package goal19b;
import java.util.*;

/**
 * Extracted production structure bodies of the industrial turbine (dims/offset, seven port extras, lever, proxy entities, connection
 * positions) and the inherited generic DummyableBlock placement/teardown bodies. Engine world, loot, sound and chat are declared services.
 * Every expected value comes from the original (cited per section) or an independent model in this file, never from the method under test.
 */
public class Goal19BStructureRegression {
    static int checks,scenarios;
    static final BlockPos CORE=new BlockPos(0,64,0);
    static final Direction[] FACINGS={Direction.NORTH,Direction.SOUTH,Direction.WEST,Direction.EAST};
    static void check(boolean v,String s){checks++;if(!v)throw new AssertionError(s);}

    /** ForgeDirection.getRotation(UP) of the original (rotation matrix row for UP): NORTH->EAST, EAST->SOUTH, SOUTH->WEST, WEST->NORTH. */
    static Direction rot(Direction f){return switch(f){case NORTH->Direction.EAST;case EAST->Direction.SOUTH;case SOUTH->Direction.WEST;case WEST->Direction.NORTH;default->throw new AssertionError();};}
    /** Original frame of TileEntityMachineIndustrialTurbine.java:201-226 and MachineIndustrialTurbine.java:76-86: core + r*rot + y*up + d*facing. */
    static BlockPos at(BlockPos core,Direction f,int r,int y,int d){Direction q=rot(f);return core.offset(r*q.dx+d*f.dx,y,r*q.dz+d*f.dz);}
    /** Original dims {2,0,3,3,1,1} (MachineIndustrialTurbine.java:73) in that frame: 3 high, 1 to each side, 3 to the front and 3 to the back = 63 cells. */
    static Set<BlockPos> footprint(BlockPos core,Direction f){
        Set<BlockPos> cells=new HashSet<>();
        for(int d=-3;d<=3;d++)for(int r=-1;r<=1;r++)for(int y=0;y<=2;y++)cells.add(at(core,f,r,y,d));
        return cells;
    }
    /**
     * Port table of MachineIndustrialTurbine.getAllPorts (:76-86): {right, up, along facing, face x, face y, face z} with the faces
     * EAST, WEST, EAST, WEST, UP, UP, NORTH in the unrotated frame.
     */
    static final int[][] TABLE={{1,0,3,1,0,0},{-1,0,3,-1,0,0},{1,0,-1,1,0,0},{-1,0,-1,-1,0,0},{0,2,3,0,1,0},{0,2,-1,0,1,0},{0,1,-3,0,0,-1}};
    /** BlockDummyable.rotatePorts (d31426c :597-629); {@code corrected} is its final loop "port += facing * -getOffset()" (:624-628, from 7df08fde1). */
    static int[][] rotatePorts(int[][] ports,Direction f,int offset,boolean corrected){
        Direction q=rot(f);int[][] result=new int[ports.length][6];
        for(int i=0;i<ports.length;i++){
            int nx=ports[i][0],ny=ports[i][1],nz=ports[i][2],ex=ports[i][3],ey=ports[i][4],ez=ports[i][5];
            result[i][0]=nx*q.dx+nz*f.dx;result[i][1]=ny;result[i][2]=nx*q.dz+nz*f.dz;
            result[i][3]=ex*q.dx+ez*f.dx;result[i][4]=ey;result[i][5]=ex*q.dz+ez*f.dz;
        }
        if(corrected)for(int[] port:result){port[0]+=f.dx*-offset;port[2]+=f.dz*-offset;}
        return result;
    }
    static Direction faceOf(int[] port){for(Direction d:Direction.values())if(d.dx==port[3]&&d.dy==port[4]&&d.dz==port[5])return d;throw new AssertionError("no valid direction");}
    /** The seven extras in the tile entity's core-relative definition (TileEntityMachineIndustrialTurbine.java:201-226). */
    static List<BlockPos> expectedPorts(BlockPos core,Direction f){
        List<BlockPos> ports=new ArrayList<>();
        for(int[] t:TABLE)ports.add(at(core,f,t[0],t[1],t[2]));
        return ports;
    }
    /** Dummy link of XR.fillSpace: first vertical towards the core's layer, then along x, then along z. */
    static BlockPos parent(BlockPos core,BlockPos c){
        int dx=c.x()-core.x(),dy=c.y()-core.y(),dz=c.z()-core.z();
        if(dy!=0)return c.offset(0,-Integer.signum(dy),0);
        if(dx!=0)return c.offset(-Integer.signum(dx),0,0);
        return c.offset(0,0,-Integer.signum(dz));
    }
    static boolean chainsThrough(BlockPos core,BlockPos cell,BlockPos root){
        for(BlockPos cur=cell;!cur.equals(core);cur=parent(core,cur))if(cur.equals(root))return true;
        return false;
    }
    static Set<BlockPos> occupied(Level l,Block b){Set<BlockPos> s=new HashSet<>();for(var e:l.states.entrySet())if(e.getValue().getBlock()==b)s.add(e.getKey());return s;}
    static void place(IndustrialTurbine b,Level l,BlockPos core,Direction f,Player p,ItemStack stack){
        // Offset 3: setPlacedBy moves the core three cells against the facing from the clicked cell, so the clicked cell is core+3*facing.
        BlockPos clicked=core.relative(f,3);BlockState s=b.defaultBlockState().setValue(DummyableBlock.FACING,f);
        l.states.put(clicked,s);b.setPlacedBy(l,clicked,s,p,stack);stack.consume(p);
    }
    static MachineIndustrialTurbineBlockEntity install(IndustrialTurbine b,Level l,BlockPos core){
        BlockEntity e=b.newBlockEntity(core,l.getBlockState(core));l.blockEntities.put(core,e);return (MachineIndustrialTurbineBlockEntity)e;
    }

    public static void main(String[] args){
        // The extracted bodies are exactly these; onRemove and playerWillDestroy are inherited from the generic DummyableBlock.
        Set<String> declared=new TreeSet<>();for(var m:IndustrialTurbine.class.getDeclaredMethods())declared.add(m.getName());
        check(declared.equals(new TreeSet<>(List.of("newBlockEntity","getDimensions","getOffset","useWithoutItem","fillSpace"))),"turbine overrides neither onRemove nor playerWillDestroy "+declared);

        for(Direction f:FACINGS){
            // 1. Placement geometry, ownership, proxies and connection positions.
            scenarios++;var b=new IndustrialTurbine();Level l=new Level();Player p=new Player();ItemStack stack=new ItemStack(64);stack.components.put("custom","keep");
            Set<BlockPos> cells=footprint(CORE,f);place(b,l,CORE,f,p,stack);
            check(cells.size()==63&&occupied(l,b).equals(cells),"original 3x3x7 box "+f+" "+occupied(l,b).size());
            check(DummyableBlock.isCore(l.getBlockState(CORE))&&l.getBlockState(CORE).getValue(DummyableBlock.FACING)==f,"core at offset 3 with facing "+f);
            check(DummyableBlock.safeRem==false,"placement restores safeRem");
            check(stack.count==63&&stack.components.equals(Map.of("custom","keep")),"normal placement consumes exactly one item and keeps components");
            BlockPos clicked=CORE.offset(3*f.dx,0,3*f.dz);
            check(cells.contains(clicked)&&l.getBlockState(clicked).getValue(DummyableBlock.TYPE)==DummyBlockType.DUMMY,"the clicked cell core+3*facing is a plain dummy");
            List<BlockPos> ports=expectedPorts(CORE,f);Set<BlockPos> expected=new HashSet<>(ports);
            check(expected.size()==7&&cells.containsAll(expected)&&!expected.contains(CORE),"seven distinct ports inside the box, none the core");
            Set<BlockPos> extras=new HashSet<>();int cores=0,dummies=0;
            for(BlockPos cell:cells){
                check(CORE.equals(b.findCore(l,cell)),"owned core reachability "+f+cell);
                BlockState s=l.getBlockState(cell);BlockEntity entity=b.newBlockEntity(cell,s);
                DummyBlockType type=s.getValue(DummyableBlock.TYPE);
                if(type==DummyBlockType.EXTRA){
                    extras.add(cell);
                    check(entity instanceof ProxyComboBlockEntity&&((ProxyComboBlockEntity)entity).fluid&&((ProxyComboBlockEntity)entity).power&&!((ProxyComboBlockEntity)entity).inventory,"proxy fluid and power, no inventory");
                }else if(type==DummyBlockType.DUMMY){dummies++;check(entity==null,"plain dummy has no block entity");}
                else{cores++;check(cell.equals(CORE)&&entity instanceof MachineIndustrialTurbineBlockEntity,"core block entity is the turbine");}
                if(!cell.equals(CORE))check(cell.relative(s.getValue(DummyableBlock.FACING).getOpposite()).equals(parent(CORE,cell)),"dummy link towards the core "+f+cell);
            }
            check(extras.equals(expected),"exact seven extras "+f+" "+extras);
            check(cores==1&&dummies==55,"one core, seven extras, 55 plain dummies "+cores+"/"+dummies);
            BlockPos lever=at(CORE,f,0,1,3);
            check(lever.equals(CORE.offset(3*f.dx,1,3*f.dz))&&cells.contains(lever)&&!expected.contains(lever)&&l.getBlockState(lever).getValue(DummyableBlock.TYPE)==DummyBlockType.DUMMY,"lever cell core+3*facing+1 is a plain dummy inside the box");

            MachineIndustrialTurbineBlockEntity be=install(b,l,CORE);
            check(be.getBlockPos().equals(CORE)&&be.getBlockState().getValue(DummyableBlock.FACING)==f,"block entity shell reads the core state");
            BlockPos placed=CORE.relative(f,3);
            int[][] literal=rotatePorts(TABLE,f,3,true);
            DirPos[] connections=be.getConPos();
            check(connections.length==6,"six fluid connections");
            Set<BlockPos> externals=new HashSet<>(),portsSeen=new HashSet<>();
            for(int i=0;i<6;i++){
                BlockPos port=ports.get(i);Direction face=faceOf(literal[i]);
                check(connections[i].makeCompat().equals(port.relative(face)),"fluid connection outside port "+i+" "+f+connections[i].makeCompat());
                check(connections[i].getDir()==face,"fluid connection direction "+i+" "+f+connections[i].getDir());
                BlockPos external=connections[i].makeCompat(),behind=external.relative(connections[i].getDir().getOpposite());
                check(!cells.contains(external),"fluid connection external to the 63 cells");
                check(behind.equals(port)&&extras.contains(behind)&&portsSeen.add(behind)&&externals.add(external),"fluid connection is the outward neighbour of exactly one distinct port "+i);
            }
            check(connections[0].getDir()==rot(f)&&connections[1].getDir()==rot(f).getOpposite()&&connections[2].getDir()==rot(f)&&connections[3].getDir()==rot(f).getOpposite()&&connections[4].getDir()==Direction.UP&&connections[5].getDir()==Direction.UP,"fluid directions rot, rot.opp, rot, rot.opp, UP, UP");
            DirPos[] power=be.getPowerPos();
            check(power.length==1,"one power connection");
            BlockPos powerPort=ports.get(6);Direction powerFace=faceOf(literal[6]);
            check(power[0].makeCompat().equals(powerPort.relative(powerFace)),"power connection outside the power port "+f+power[0].makeCompat());
            check(power[0].getDir()==f.getOpposite()&&powerFace==f.getOpposite(),"power connection direction is the facing opposite");
            check(!cells.contains(power[0].makeCompat())&&power[0].makeCompat().relative(power[0].getDir().getOpposite()).equals(powerPort)&&!externals.contains(power[0].makeCompat()),"power connection external and distinct from the fluid connections");

            // The original's own port table (placed block + rotatePorts incl. the offset correction, d31426c) is the same seven cells; the
            // uncorrected 7f74257e1 intermediate state added the core-relative table to the placed block and shifted it by 3*facing.
            for(int i=0;i<7;i++){
                BlockPos lp=placed.offset(literal[i][0],literal[i][1],literal[i][2]);
                check(lp.equals(ports.get(i)),"original d31426c placed+rotatePorts equals the core-relative port "+i+" "+f);
            }
            int[][] intermediate=rotatePorts(TABLE,f,3,false);int outside=0;
            for(int i=0;i<7;i++){
                BlockPos lp=placed.offset(intermediate[i][0],intermediate[i][1],intermediate[i][2]);
                check(!lp.equals(ports.get(i))&&lp.equals(ports.get(i).relative(f,3)),"uncorrected 7f74257e1 table is shifted by 3*facing "+i);
                if(!cells.contains(lp))outside++;
            }
            check(outside==3,"uncorrected 7f74257e1 table lands three ports outside the box");

            // Placement does not need the cells outside the box: blocked connection cells leave placement intact.
            scenarios++;l=new Level();Block solid=new Block();
            for(DirPos c:connections)l.states.put(c.makeCompat(),solid.defaultBlockState());
            l.states.put(power[0].makeCompat(),solid.defaultBlockState());
            place(b,l,CORE,f,p,new ItemStack(4));
            check(occupied(l,b).equals(cells),"blocked outside connection cells do not block placement "+f);

            // 2. Blocked placement: every cell but the clicked one refunds the stack with components and leaves no partial structure.
            for(BlockPos obstacle:cells){
                if(obstacle.equals(clicked))continue;
                scenarios++;Level bad=new Level();Block other=new Block();bad.states.put(obstacle,other.defaultBlockState());ItemStack refund=new ItemStack(64);refund.components.put("custom","keep");place(b,bad,CORE,f,p,refund);
                check(refund.count==64&&refund.components.equals(Map.of("custom","keep")),"blocked at-limit refund keeps components");
                check(occupied(bad,b).isEmpty()&&bad.getBlockState(obstacle).getBlock()==other&&!DummyableBlock.safeRem,"blocked no partial structure");
            }
            scenarios++;Player creative=new Player();creative.creative=true;Level blocked=new Level();Block stone=new Block();blocked.states.put(CORE.above(2),stone.defaultBlockState());ItemStack kept=new ItemStack(64);place(b,blocked,CORE,f,creative,kept);
            check(kept.count==64&&occupied(blocked,b).isEmpty(),"creative blocked placement changes nothing");

            // 3. Teardown by the inherited generic path: whole structure, one drop, independent neighbours survive.
            Direction side=rot(f);
            List<BlockPos> neighbours=List.of(CORE.relative(side,3),CORE.relative(side.getOpposite(),3),CORE.relative(f,7),CORE.relative(f.getOpposite(),7));
            for(BlockPos neighbour:neighbours)for(boolean direct:new boolean[]{false,true})for(BlockPos removed:cells){
                scenarios++;l=new Level();place(b,l,CORE,f,p,new ItemStack(4));place(b,l,neighbour,f,p,new ItemStack(4));
                BlockState old=l.getBlockState(removed);if(!direct)b.playerWillDestroy(l,removed,old,p);l.removeBlock(removed,false);
                check(occupied(l,b).equals(footprint(neighbour,f)),"whole structure removed, independent neighbour intact "+f+removed+neighbour);
                check(!DummyableBlock.safeRem,"teardown restores safeRem");
                check(l.drops==(direct?0:1),"survival machine loot exactly once on the player path only "+l.drops);
            }
            for(BlockPos removed:cells){
                scenarios++;l=new Level();place(b,l,CORE,f,p,new ItemStack(4));
                BlockState old=l.getBlockState(removed);b.playerWillDestroy(l,removed,old,creative);l.removeBlock(removed,false);
                check(occupied(l,b).isEmpty()&&l.drops==0&&!DummyableBlock.safeRem,"creative break removes everything without loot "+f+removed);
            }
            for(BlockPos replaced:cells){
                scenarios++;l=new Level();place(b,l,CORE,f,p,new ItemStack(4));BlockPos neighbour=neighbours.get(0);place(b,l,neighbour,f,p,new ItemStack(4));Block replacement=new Block();l.setBlock(replaced,replacement.defaultBlockState(),3);
                check(l.getBlockState(replaced).getBlock()==replacement&&occupied(l,b).equals(footprint(neighbour,f)),"nonair replacement preserved, structure gone, neighbour intact "+f+replaced);
                check(!DummyableBlock.safeRem,"replacement restores safeRem");
            }
            for(BlockPos foreign:List.of(CORE.above(3),CORE.relative(f,4),CORE.relative(f.getOpposite(),4),CORE.relative(side,2),CORE.below())){
                scenarios++;l=new Level();place(b,l,CORE,f,p,new ItemStack(4));l.states.put(foreign,b.defaultBlockState().setValue(DummyableBlock.FACING,f));l.removeBlock(CORE,false);
                check(l.getBlockState(foreign).getBlock()==b&&DummyableBlock.isCore(l.getBlockState(foreign))&&occupied(l,b).equals(Set.of(foreign)),"foreign core just outside the box preserved, structure gone "+f+foreign);
            }
            // A foreign core inside the box keeps exactly the cells whose chain runs through it; the rest is orphaned and removed.
            for(BlockPos inside:cells){
                if(inside.equals(CORE))continue;
                scenarios++;l=new Level();place(b,l,CORE,f,p,new ItemStack(4));l.states.put(inside,b.defaultBlockState().setValue(DummyableBlock.FACING,f.getOpposite()));l.removeBlock(CORE,false);
                Set<BlockPos> survivors=new HashSet<>();for(BlockPos cell:cells)if(!cell.equals(CORE)&&chainsThrough(CORE,cell,inside))survivors.add(cell);
                check(l.getBlockState(inside).getBlock()==b&&DummyableBlock.isCore(l.getBlockState(inside)),"unowned core inside the box preserved "+f+inside);
                check(l.getBlockState(CORE).getBlock()!=b,"the removed core is gone "+f+inside);
                check(occupied(l,b).equals(survivors),"exactly the cells chaining through the unowned core survive "+f+inside);
                for(BlockPos remaining:occupied(l,b))check(inside.equals(b.findCore(l,remaining)),"every surviving cell chains to the unowned core "+f+inside+remaining);
            }
            // The orphan cascade is the production destroyIfOrphan and honours its chunk-border guard.
            scenarios++;l=new Level();place(b,l,CORE,f,p,new ItemStack(4));l.chunksLoaded=false;l.removeBlock(CORE,false);
            check(occupied(l,b).size()==62,"unloaded chunk border keeps the dummies "+occupied(l,b).size());

            // 4. Lever (original onBlockActivated :44-71): only the lever cell, not sneaking, acts.
            scenarios++;l=new Level();place(b,l,CORE,f,p,new ItemStack(4));be=install(b,l,CORE);
            for(BlockPos cell:cells)for(boolean sneak:new boolean[]{false,true})for(boolean client:new boolean[]{false,true})for(boolean operational:new boolean[]{false,true}){
                scenarios++;l.sounds.clear();p.messages.clear();be.leverPulls=0;be.operational=operational;l.isClientSide=client;p.sneak=sneak;
                InteractionResult result=b.useWithoutItem(l.getBlockState(cell),l,cell,p,new BlockHitResult());
                boolean acts=cell.equals(lever)&&!sneak;
                boolean pull=acts&&!client&&!operational,locked=acts&&!client&&operational;
                String where=" "+f+cell+" sneak="+sneak+" client="+client+" operational="+operational;
                check(result==(acts?(client?InteractionResult.SUCCESS:InteractionResult.CONSUME):InteractionResult.PASS),"lever result"+where+" "+result);
                check(be.leverPulls==(pull?1:0),"lever pull count"+where+" "+be.leverPulls);
                check(l.sounds.size()==(pull?1:0),"lever sound count"+where+" "+l.sounds.size());
                if(pull){
                    PlayedSound sound=l.sounds.get(0);
                    check(sound.pos().x==cell.x()+0.5&&sound.pos().y==cell.y()+0.5&&sound.pos().z==cell.z()+0.5,"lever sound position"+where);
                    check(sound.event()==NtmSoundEvents.TURBINE_LEVER.get(),"lever sound event"+where);
                    check(sound.source()==SoundSource.BLOCKS,"lever sound source"+where);
                    check(sound.volume()==1.5F,"lever sound volume"+where+" "+sound.volume());
                    check(sound.pitch()==1.0F,"lever sound pitch"+where);
                }
                check(p.messages.size()==(locked?1:0),"lever message count"+where+" "+p.messages.size());
                if(locked){
                    Component message=p.messages.get(0);
                    check(message.key.equals("machine_industrial_turbine.compressor_locked"),"lever message key"+where);
                    check(message.styles.equals(List.of(ChatFormatting.RED)),"lever message style"+where+" "+message.styles);
                }
            }
            l.isClientSide=false;p.sneak=false;p.messages.clear();

            // A dangling dummy has no core: the click is consumed on both sides, except when sneaking (original :43-44, :70).
            for(boolean sneak:new boolean[]{false,true})for(boolean client:new boolean[]{false,true}){
                scenarios++;Level lone=new Level();BlockPos orphan=CORE.offset(2,0,5);
                lone.states.put(orphan,b.defaultBlockState().setValue(DummyableBlock.TYPE,DummyBlockType.DUMMY).setValue(DummyableBlock.FACING,f));
                lone.isClientSide=client;Player q=new Player();q.sneak=sneak;
                InteractionResult result=b.useWithoutItem(lone.getBlockState(orphan),lone,orphan,q,new BlockHitResult());
                check(result==(sneak?InteractionResult.PASS:(client?InteractionResult.SUCCESS:InteractionResult.CONSUME)),"missing core consumes the click "+f+" sneak="+sneak+" client="+client+" "+result);
                check(lone.sounds.isEmpty()&&q.messages.isEmpty(),"missing core has no effects");
            }
            // A core without the turbine block entity (absent or foreign type) does nothing, even at the lever cell.
            for(BlockEntity wrong:new BlockEntity[]{null,new ProxyComboBlockEntity(CORE,l.getBlockState(CORE))}){
                scenarios++;Level bare=new Level();place(b,bare,CORE,f,p,new ItemStack(4));if(wrong!=null)bare.blockEntities.put(CORE,wrong);
                Player q=new Player();InteractionResult result=b.useWithoutItem(bare.getBlockState(lever),bare,lever,q,new BlockHitResult());
                check(result==InteractionResult.PASS&&bare.sounds.isEmpty()&&q.messages.isEmpty(),"no turbine block entity at the core passes "+f);
            }
        }
        System.out.println("Goal19B structures: "+checks+" assertions; "+scenarios+" independent scenarios; 0 executed ticks");
    }
}
