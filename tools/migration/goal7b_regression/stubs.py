"""Goal 7B stand-ins: the Goal 6 services with the real fluid network, pipes and barrels restored."""

from goal6_regression.stubs import build_stubs as goal6_stubs


def _require(text, old, label):
    if old not in text:
        raise SystemExit(f"Goal 7B stub anchor missing in {label}: {old[:60]}")
    return text


def _replace(stubs, name, old, new):
    stubs[name] = _require(stubs[name], old, name).replace(old, new)


def build_stubs(source):
    stubs = goal6_stubs(source)

    # Goal 5C/6 replaced the fluid network with inert interfaces; Goal 7B compiles the production ones.
    for name in ("api/hbm/fluidmk2/IFluidReceiverMK2.java",
                 "api/hbm/fluidmk2/IFluidStandardReceiverMK2.java",
                 "api/hbm/fluidmk2/IFluidStandardTransceiverMK2.java"):
        stubs.pop(name)
    _replace(stubs, "com/hbm/blockentity/LoadedBaseBlockEntity.java",
             "public void trySubscribe(FluidType t,Level l,DirPos p){}public void tryProvide(FluidTank t,Level l,DirPos p){}",
             "public boolean tilted;public int getFloorCount(){return 0;}public BlockPos getFloorPosFromIndex(int i){return null;}")

    # 3D data values follow the 1.21 get3DDataValue order; Direction.Plane comes from the Goal 3B base stand-in.
    _replace(stubs, "net/minecraft/core/Direction.java", "public enum Axis{",
             "public int get3DDataValue(){return switch(this){case DOWN->0;case UP->1;case NORTH->2;case SOUTH->3;case WEST->4;case EAST->5;};}"
             "public enum Axis{")

    # Fluid types carry the production network provider and the barrel's destructive traits as plain flags.
    _replace(stubs, "com/hbm/inventory/fluid/FluidType.java", "public int getTint(){return 0;}",
             "private com.hbm.uninos.networkproviders.FluidNetProvider provider;"
             "public com.hbm.uninos.INetworkProvider<api.hbm.fluidmk2.FluidNetMK2> getNetworkProvider(){"
             "if(provider==null)provider=new com.hbm.uninos.networkproviders.FluidNetProvider(this);return provider;}"
             "public boolean hot,corrosive,highlyCorrosive,antimatter;public boolean isHot(){return hot;}public boolean isCorrosive(){return corrosive;}"
             "public boolean isHighlyCorrosive(){return highlyCorrosive;}"
             "public boolean isAntimatter(){return antimatter;}public int getColor(){return 0;}public String getUnlocalizedName(){return \"fluid:\"+id;}"
             "public int getTint(){return 0;}")

    # Blocks are identities only: the barrel compares its block with NtmBlocks and reads the capacity from BarrelBlock.
    # A steel barrel holding a highly corrosive fluid replaces itself with the default corroded barrel state (Goal 19A).
    stubs["net/minecraft/world/level/block/Block.java"] = (
        "package net.minecraft.world.level.block;public class Block{public net.minecraft.world.level.block.state.BlockState defaultBlockState(){"
        "net.minecraft.world.level.block.state.BlockState s=new net.minecraft.world.level.block.state.BlockState();s.block=this;return s;}}")
    stubs["com/hbm/blocks/machine/BarrelBlock.java"] = (
        "package com.hbm.blocks.machine;public class BarrelBlock extends net.minecraft.world.level.block.Block{"
        "private final int capacity;public BarrelBlock(int c){capacity=c;}public int getCapacity(){return capacity;}}")
    _replace(stubs, "net/minecraft/world/level/block/state/BlockState.java",
             "public Object getBlock(){return this;}",
             "public net.minecraft.world.level.block.Block block=new net.minecraft.world.level.block.Block();"
             "public net.minecraft.world.level.block.Block getBlock(){return block;}")
    _replace(stubs, "com/hbm/blocks/NtmBlocks.java", "public class NtmBlocks{",
             "public class NtmBlocks{public static final BlockRef BARREL_PLASTIC=new BlockRef(new com.hbm.blocks.machine.BarrelBlock(12_000)),"
             "BARREL_STEEL=new BlockRef(new com.hbm.blocks.machine.BarrelBlock(16_000)),"
             "BARREL_CORRODED=new BlockRef(new com.hbm.blocks.machine.BarrelBlock(16_000));"
             "public static class BlockRef{private final net.minecraft.world.level.block.Block b;public BlockRef(net.minecraft.world.level.block.Block b){this.b=b;}"
             "public net.minecraft.world.level.block.Block get(){return b;}}")
    _replace(stubs, "com/hbm/blockentity/NtmBlockEntityTypes.java", "BATTERY_SOCKET=new Ref()",
             "BATTERY_SOCKET=new Ref(),FLUID_DUCT=new Ref(),BARREL=new Ref()")

    # World effects of the barrel's fluid interaction are recorded, not simulated.
    _replace(stubs, "net/minecraft/world/level/Level.java", "public void addParticle(",
             "public final List<BlockPos> destroyed=new ArrayList<>();public int explosions,comparatorUpdates;"
             "public boolean destroyBlock(BlockPos p,boolean drop){destroyed.add(p);return true;}"
             "public final List<BlockPos> replaced=new ArrayList<>();public boolean setBlock(BlockPos p,BlockState s,int flags){replaced.add(p);return true;}"
             "public enum ExplosionInteraction{TNT}public Object explode(Object e,double x,double y,double z,float r,ExplosionInteraction i){explosions++;return null;}"
             "public void updateNeighbourForOutputSignal(BlockPos p,Object b){comparatorUpdates++;}"
             "public void addParticle(")
    _replace(stubs, "net/minecraft/sounds/SoundEvents.java", "FIRECHARGE_USE=new Object()",
             "FIRECHARGE_USE=new Object(),FIRE_EXTINGUISH=new Object()")
    # The corroded barrel's leak dispatches a SPILL release to the fluid's traits; these fluids carry none.
    stubs["com/hbm/inventory/fluid/trait/FluidTrait.java"] = (
        "package com.hbm.inventory.fluid.trait;public class FluidTrait{public enum FluidReleaseType{VOID,BURN,SPILL}"
        "public static void onRelease(net.minecraft.world.level.Level l,net.minecraft.core.BlockPos p,com.hbm.inventory.fluid.FluidType t,"
        "com.hbm.inventory.fluid.tank.FluidTank tank,FluidReleaseType r,int mB){}}")

    # The barrel menu is outside this regression; the pipe's copy tool path needs only its declared types.
    stubs["com/hbm/inventory/menus/BarrelMenu.java"] = (
        "package com.hbm.inventory.menus;public class BarrelMenu extends net.minecraft.world.inventory.AbstractContainerMenu{"
        "public BarrelMenu(int id,net.minecraft.world.entity.player.Inventory inv,Object be){}}")
    stubs["com/hbm/blockentity/IFluidCopiable.java"] = (
        "package com.hbm.blockentity;import com.hbm.inventory.fluid.tank.FluidTank;import net.minecraft.core.BlockPos;"
        "import net.minecraft.nbt.CompoundTag;import net.minecraft.world.entity.player.Player;import net.minecraft.world.level.Level;"
        "public interface IFluidCopiable{FluidTank getTankToPaste();default int[] getFluidIDToCopy(){return new int[0];}"
        "default void pasteSettings(CompoundTag t,int i,Level l,Player p,BlockPos pos){}}")
    stubs["com/hbm/blocks/network/IBlockFluidDuct.java"] = (
        "package com.hbm.blocks.network;public interface IBlockFluidDuct{void changeTypeRecursively("
        "net.minecraft.world.level.Level l,net.minecraft.core.BlockPos p,com.hbm.inventory.fluid.FluidType t,int loops);}")
    stubs["com/hbm/handler/HbmKeybinds.java"] = (
        "package com.hbm.handler;public class HbmKeybinds{public enum EnumKeybind{TOOL_CTRL}}")
    stubs["com/hbm/extprop/HbmPlayerAttachments.java"] = (
        "package com.hbm.extprop;public class HbmPlayerAttachments{public boolean getKeyPressed(Object k){return false;}}")
    stubs["com/hbm/lib/ModAttachments.java"] = (
        "package com.hbm.lib;public class ModAttachments{public static final Ref PLAYER_ATTACHMENT=new Ref();"
        "public static class Ref{public Object get(){return null;}}}")
    _replace(stubs, "net/minecraft/world/entity/player/Player.java", "public boolean isShiftKeyDown(){return false;}",
             "public boolean isShiftKeyDown(){return false;}public <T> T getData(Object type){return null;}")
    _replace(stubs, "com/hbm/util/fauxpointtwelve/DirPos.java", "public int getX(){return x;}",
             "public DirPos(BlockPos p,Direction d){this(p.getX(),p.getY(),p.getZ(),d);}public int getX(){return x;}")
    _replace(stubs, "net/minecraft/nbt/CompoundTag.java", "public void putInt(String k,int v)",
             "public int[] getIntArray(String k){return m.get(k) instanceof int[] a?a:new int[0];}public void putInt(String k,int v)")
    _replace(stubs, "net/minecraft/world/entity/player/Player.java", "public double distanceToSqr(BlockPos.Vec p){return 0;}",
             "public double distanceToSqr(BlockPos.Vec p){return 0;}public double distanceToSqr(double x,double y,double z){return 0;}")
    return stubs
