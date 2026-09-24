"""Minecraft services around the live energy network, battery socket, wood burner and shredder."""

import re

from goal5c_regression.stubs import build_stubs as goal5c_stubs


def _require(text, old, label):
    if old not in text:
        raise SystemExit(f"Goal 6 stub anchor missing in {label}: {old[:60]}")
    return text


def _replace(stubs, name, old, new):
    stubs[name] = _require(stubs[name], old, name).replace(old, new)


def flammable_energy(fluids_source, name):
    """Read the literal base value that Fluids registers as FT_Flammable for one fluid."""
    match = re.search(rf"registerCalculatedFuel\({name},\s*([0-9_]+)\s*(?:/\*.*?\*/)?\s*,\s*0\s*,\s*null\)", fluids_source)
    if not match:
        raise SystemExit(f"Cannot find the calculated fuel registration for {name}")
    base = int(match.group(1).replace("_", ""))
    # Fluids.round() only trims digits below 1 000 in this range, so the registered value is the literal.
    if not (100_000 < base <= 1_000_000 and base % 1_000 == 0):
        raise SystemExit(f"{name} fuel literal {base} would be changed by Fluids.round(); update the harness")
    return base


def soot_per_second(pollution_source):
    match = re.search(r"SOOT_PER_SECOND\s*=\s*([^;]+);", pollution_source)
    if not match:
        raise SystemExit("Cannot find PollutionHandler.SOOT_PER_SECOND")
    return match.group(1).strip()


def build_stubs(source):
    stubs = goal5c_stubs(source)
    fluids_source = (source / "com/hbm/inventory/fluid/Fluids.java").read_text(encoding="utf-8")
    pollution_source = (source / "com/hbm/handler/pollution/PollutionHandler.java").read_text(encoding="utf-8")

    # These are compiled from production source in Goal 6.
    for name in ("api/hbm/energymk2/IEnergyProviderMK2.java",
                 "api/hbm/energymk2/IBatteryItem.java",
                 "api/hbm/blockentity/ILoadedBE.java",
                 "com/hbm/items/machine/BatteryPackItem.java"):
        stubs.pop(name)

    # The Goal 5C stand-in suppressed energy provision; the production interface default must be reachable.
    _replace(stubs, "com/hbm/blockentity/LoadedBaseBlockEntity.java",
             "public void tryProvide(Level l,Object p,Object d){}", "")

    _replace(stubs, "net/minecraft/world/level/Level.java", "public long getGameTime(){return time++;}",
             "public boolean manualClock;public final Set<BlockPos> powered=new HashSet<>();"
             "public long getGameTime(){return manualClock?time:time++;}"
             "public boolean hasNeighborSignal(BlockPos p){return powered.contains(p);}")
    _replace(stubs, "net/minecraft/core/Direction.java", "public enum Axis{VERTICAL,HORIZONTAL;",
             "public Direction getClockWise(Axis a){if(a!=Axis.Y)throw new UnsupportedOperationException();return getClockWise();}"
             "public enum Axis{VERTICAL,HORIZONTAL,X,Y,Z;")
    _replace(stubs, "net/minecraft/world/Container.java", "static boolean stillValidBlockEntity(Object be,Player p){return true;}",
             "static boolean stillValidBlockEntity(Object be,Player p){return be instanceof net.minecraft.world.level.block.entity.BlockEntity b"
             "&&b.getLevel()!=null&&b.getLevel().getBlockEntity(b.getBlockPos())==b&&p.inReach;}")
    _replace(stubs, "net/minecraft/world/entity/player/Player.java", "public Level world;",
             "public boolean inReach=true;public Level world;")
    _replace(stubs, "net/minecraft/network/RegistryFriendlyByteBuf.java", "public void writeLong(long n)",
             "public void writeByte(int n){v.add((byte)n);}public byte readByte(){return (byte)v.get(i++);}public void writeLong(long n)")
    _replace(stubs, "net/minecraft/world/item/Item.java",
             "public static class Properties{public Properties stacksTo(int n){return this;}}public Item(Properties p){this(\"special_item\");}",
             "public static class Properties{public int max=64;public Properties stacksTo(int n){max=n;return this;}}"
             "public Item(Properties p){this(\"special_item\",p.max,0);}"
             "private static final List<Item> IDS=new ArrayList<>();public static int getId(Item i){int n=IDS.indexOf(i);if(n<0){IDS.add(i);n=IDS.size()-1;}return n;}"
             "public static Item byId(int n){return IDS.get(n);}"
             "public int getUseDuration(ItemStack s,net.minecraft.world.entity.LivingEntity e){return 0;}"
             "public boolean isBarVisible(ItemStack s){return false;}public int getBarWidth(ItemStack s){return 0;}public int getBarColor(ItemStack s){return 0;}")
    _replace(stubs, "net/minecraft/world/item/ItemStack.java", "public int getMaxDamage()",
             "public boolean isDamageableItem(){return getMaxDamage()>0;}public int getMaxDamage()")
    _replace(stubs, "net/minecraft/util/Mth.java", "public class Mth{",
             "public class Mth{public static int hsvToRgb(float h,float s,float v){return 0;}")
    _replace(stubs, "com/hbm/util/BobMathUtil.java", "public class BobMathUtil{",
             "public class BobMathUtil{public static String getShortNumber(long n){return String.valueOf(n);}")
    _replace(stubs, "com/hbm/main/NuclearTechMod.java", "public class NuclearTechMod{",
             "public class NuclearTechMod{public static net.minecraft.resources.ResourceLocation withDefaultNamespace(String p){"
             "return net.minecraft.resources.ResourceLocation.fromNamespaceAndPath(\"hbmsntm\",p);}")
    _replace(stubs, "net/neoforged/neoforge/network/PacketDistributor.java", "public class PacketDistributor{",
             "public class PacketDistributor{public static void sendToPlayersNear(Object a,Object b,double x,double y,double z,int range,Object packet){}")
    _replace(stubs, "com/hbm/lib/Library.java", "public class Library{",
             "public class Library{public static final net.minecraft.core.Direction POS_X=net.minecraft.core.Direction.EAST,"
             "NEG_X=net.minecraft.core.Direction.WEST,POS_Y=net.minecraft.core.Direction.UP,NEG_Y=net.minecraft.core.Direction.DOWN,"
             "POS_Z=net.minecraft.core.Direction.SOUTH,NEG_Z=net.minecraft.core.Direction.NORTH;"
             "public static long chargeTEFromItems(NonNullList<ItemStack> s,int i,long p,long m){return p;}")
    _replace(stubs, "net/minecraft/world/level/block/entity/BlockEntity.java", "public void onChunkUnloaded(){}",
             "public void onChunkUnloaded(){}public void setChanged(){}")
    _replace(stubs, "net/minecraft/nbt/CompoundTag.java", "public void putLong(String k,long v)",
             "public void putByte(String k,byte v){m.put(k,v);}public byte getByte(String k){return (byte)m.getOrDefault(k,(byte)0);}public void putLong(String k,long v)")
    _replace(stubs, "com/hbm/blockentity/NtmBlockEntityTypes.java", "MACHINE_SHREDDER=new Ref()",
             "MACHINE_SHREDDER=new Ref(),BATTERY_SOCKET=new Ref()")
    stubs["com/hbm/inventory/NtmMenuTypes.java"] = (
        "package com.hbm.inventory;import net.minecraft.world.inventory.*;public class NtmMenuTypes{public static final Ref "
        "HEATER_FIREBOX=new Ref(),FURNACE_COMBINATION=new Ref(),MACHINE_SHREDDER=new Ref(),BATTERY_SOCKET=new Ref();"
        "public static class Ref{public <T extends AbstractContainerMenu> MenuType<T> get(){return new MenuType<>();}}}"
    )

    items = stubs["com/hbm/items/NtmItems.java"]
    extra = {
        "BLADES_STEEL": 'new Ref(new Item("hbmsntm:blades_steel",1,0,256))',
        "BLADES_TITANIUM": 'new Ref(new Item("hbmsntm:blades_titanium",1,0,512))',
        "BLADES_DESH": 'new Ref(new Item("hbmsntm:blades_desh",1,0,0))',
        "DUST": 'new Ref("hbmsntm:dust")',
    }
    for name, value in extra.items():
        if re.search(rf"\b{name}=", items):
            raise SystemExit(f"NtmItems stand-in already defines {name}")
        items = _require(items, "FLUID_IDENTIFIER_MULTI=", "NtmItems").replace(
            "FLUID_IDENTIFIER_MULTI=", f"{name}={value},FLUID_IDENTIFIER_MULTI=", 1)
    stubs["com/hbm/items/NtmItems.java"] = items
    stubs["com/hbm/inventory/recipes/ShredderRecipes.java"] = """package com.hbm.inventory.recipes;import java.util.*;import net.minecraft.world.item.*;
public class ShredderRecipes {private static final Map<Item,ItemStack> outputs=new HashMap<>();public static void set(Item i,ItemStack o){outputs.put(i,o);}
 public static ItemStack getShredderResult(ItemStack s){if(s.isEmpty())return ItemStack.EMPTY;ItemStack o=outputs.get(s.getItem());return o==null?new ItemStack(com.hbm.items.NtmItems.DUST.get()):o.copy();}}"""
    _replace(stubs, "net/minecraft/sounds/SoundEvents.java", "FIRECHARGE_USE=new Object()",
             "FIRECHARGE_USE=new Object(),MINECART_RIDING=new Object()")

    stubs["com/hbm/items/EnumMultiItem.java"] = (
        "package com.hbm.items;import java.util.*;import net.minecraft.world.item.*;"
        "public class EnumMultiItem extends Item{protected final Class<? extends Enum<?>> theEnum;"
        "public EnumMultiItem(Properties p,Class<? extends Enum<?>> e,boolean multiName,boolean multiTexture){super(p);theEnum=e;}"
        "public void getSubItems(Item item,List<ItemStack> stacks){}}"
    )
    stubs["com/hbm/interfaces/ICopiable.java"] = (
        "package com.hbm.interfaces;import net.minecraft.core.BlockPos;import net.minecraft.nbt.CompoundTag;"
        "import net.minecraft.world.entity.player.Player;import net.minecraft.world.level.Level;"
        "public interface ICopiable{CompoundTag getSettings(Level l,BlockPos p);void pasteSettings(CompoundTag t,int i,Level l,Player p,BlockPos pos);}"
    )

    # Pollution is recorded, not simulated; the per-second soot rate is the production constant expression.
    stubs["com/hbm/handler/pollution/PollutionHandler.java"] = (
        "package com.hbm.handler.pollution;import net.minecraft.world.level.Level;import net.minecraft.core.BlockPos;"
        "public class PollutionHandler{public enum PollutionType{SOOT,POISON,HEAVYMETAL,FALLOUT}"
        f"public static final float SOOT_PER_SECOND={soot_per_second(pollution_source)};"
        "public static float soot;public static int calls;public static void reset(){soot=0;calls=0;}"
        "public static void incrementPollution(Level l,BlockPos p,PollutionType t,float n){if(t==PollutionType.SOOT){soot+=n;calls++;}}}"
    )
    stubs["com/hbm/inventory/fluid/trait/FT_Flammable.java"] = (
        "package com.hbm.inventory.fluid.trait;public class FT_Flammable{private final long energy;"
        "public FT_Flammable(long e){energy=e;}public long getHeatEnergy(){return energy;}}"
    )
    _replace(stubs, "com/hbm/inventory/fluid/FluidType.java", "public <T> T getTrait(Class<T> c){return null;}",
             "public final Map<Class<?>,Object> traits=new HashMap<>();@SuppressWarnings(\"unchecked\")public <T> T getTrait(Class<T> c){return (T)traits.get(c);}")
    _replace(stubs, "com/hbm/inventory/fluid/Fluids.java", "public static FluidType[] getAll()",
             "static{COALCREOSOTE.traits.put(com.hbm.inventory.fluid.trait.FT_Flammable.class,new com.hbm.inventory.fluid.trait.FT_Flammable("
             f"{flammable_energy(fluids_source, 'COALCREOSOTE')}L));"
             "WOODOIL.traits.put(com.hbm.inventory.fluid.trait.FT_Flammable.class,new com.hbm.inventory.fluid.trait.FT_Flammable("
             f"{flammable_energy(fluids_source, 'WOODOIL')}L));}}"
             "public static FluidType[] getAll()")
    return stubs
