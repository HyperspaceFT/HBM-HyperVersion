"""Goal 9B stand-ins: the Goal 9A services plus the steam engine and condenser plumbing and the cooling traits."""

import re

from goal9a_regression.stubs import build_stubs as goal9a_stubs


def _require(text, old, label):
    if old not in text:
        raise SystemExit(f"Goal 9B stub anchor missing in {label}: {old[:60]}")
    return text


def _replace(stubs, name, old, new):
    stubs[name] = _require(stubs[name], old, name).replace(old, new)


def coolable_traits(fluids_source):
    """FT_Coolable definitions of production Fluids.java as (fluid, coolsTo, req, produced, heat, [(type, efficiency)])."""
    constants = {}
    for name, value in re.findall(r"double (\w+) = ([\d.]+)D;", fluids_source):
        if constants.setdefault(name, value) != value:
            raise SystemExit(f"Goal 9B: Fluids.java declares {name} with two values")
    found = []
    for match in re.finditer(r"(\w+)\.addTraits\(new FT_Coolable\((\w+), (\d+), (\d+), (\d+)\)((?:\.setEff\(CoolingType\.\w+, [\w.]+\))*)\)",
                             fluids_source):
        effs = [(kind, float(constants.get(value, value.rstrip("D"))))
                for kind, value in re.findall(r"setEff\(CoolingType\.(\w+), ([\w.]+)\)", match.group(6))]
        found.append((match.group(1), match.group(2), int(match.group(3)), int(match.group(4)), int(match.group(5)), effs))
    if len(found) != fluids_source.count("new FT_Coolable(") or not found:
        raise SystemExit("Goal 9B: could not parse every FT_Coolable definition in Fluids.java")
    return found


def build_stubs(source):
    stubs = goal9a_stubs(source)
    fluids_source = (source / "com/hbm/inventory/fluid/Fluids.java").read_text(encoding="utf-8")

    # ---- Registry entries -----------------------------------------------------------------------------------------
    _replace(stubs, "com/hbm/blockentity/NtmBlockEntityTypes.java", "BATTERY_SOCKET=new Ref()",
             "BATTERY_SOCKET=new Ref(),MACHINE_STEAM_ENGINE=new Ref(),MACHINE_CONDENSER=new Ref()")
    _replace(stubs, "com/hbm/registry/NtmSoundEvents.java", "ASSEMBLER_STOP=new Ref()",
             "ASSEMBLER_STOP=new Ref(),STEAM_ENGINE_OPERATE=new Ref()")

    # ---- Vanilla Mth (1.21.1 sources, see goal9b_regression/README.md) --------------------------------------------
    # clamp(float) is Mth.java:136-138, wrapDegrees(double) Mth.java:275-283; the Goal 3 helpers are kept.
    stubs["net/minecraft/util/Mth.java"] = (
        "package net.minecraft.util;public class Mth{public static int hsvToRgb(float h,float s,float v){return 0;}"
        "public static int clamp(int v,int lo,int hi){return Math.min(Math.max(v,lo),hi);}"
        "public static float clamp(float value,float min,float max){return value<min?min:Math.min(value,max);}"
        "public static double wrapDegrees(double value){double d0=value%360.0;if(d0>=180.0)d0-=360.0;if(d0<-180.0)d0+=360.0;return d0;}}")

    # ---- One buffer model ------------------------------------------------------------------------------------------
    # Earlier stand-ins kept two value lists (ByteBuf and RegistryFriendlyByteBuf), which only stays ordered by
    # accident. Here every buffer is one list of typed values with a reader index. writeBytes(ByteBuf) appends the
    # source's unread values and advances the source's reader index, as netty's AbstractByteBuf.writeBytes(ByteBuf)
    # does (writeBytes(src, src.readableBytes()) then src.readerIndex(+length)). readableBytes() counts values, not
    # bytes. values() is a stand-in accessor that reads the unread values without consuming them.
    stubs["io/netty/buffer/ByteBuf.java"] = (
        "package io.netty.buffer;import java.util.*;public class ByteBuf{private final List<Object> values=new ArrayList<>();private int reader;public int releases;"
        "protected Object next(){return values.get(reader++);}protected void put(Object v){values.add(v);}"
        "public void writeInt(int v){values.add(v);}public int readInt(){return (int)next();}"
        "public void writeShort(int v){values.add((short)v);}public short readShort(){return (short)next();}"
        "public void writeLong(long v){values.add(v);}public long readLong(){return (long)next();}"
        "public void writeFloat(float v){values.add(v);}public float readFloat(){return (float)next();}"
        "public void writeDouble(double v){values.add(v);}public double readDouble(){return (double)next();}"
        "public void writeByte(int v){values.add((byte)v);}public byte readByte(){return (byte)next();}"
        "public void writeBoolean(boolean v){values.add(v);}public boolean readBoolean(){return (boolean)next();}"
        "public void writeBytes(ByteBuf src){values.addAll(src.values.subList(src.reader,src.values.size()));src.reader=src.values.size();}"
        "public int readableBytes(){return values.size()-reader;}public boolean release(){releases++;return true;}"
        "public List<Object> values(){return List.copyOf(values.subList(reader,values.size()));}}")
    stubs["io/netty/buffer/Unpooled.java"] = (
        "package io.netty.buffer;public final class Unpooled{public static ByteBuf buffer(){return new ByteBuf();}}")
    stubs["net/minecraft/network/RegistryFriendlyByteBuf.java"] = (
        "package net.minecraft.network;public class RegistryFriendlyByteBuf extends io.netty.buffer.ByteBuf{"
        "public void writeUtf(String n){put(n);}public String readUtf(){return (String)next();}}")

    # ---- LoadedBaseBlockEntity sync and volume ---------------------------------------------------------------------
    # Production LoadedBaseBlockEntity.java:82-96: getVolume is 10 % while muffled; serialize/deserialize carry
    # muffled and tilted ahead of every subclass's data. networkPackNT stays a counter (it does not serialize).
    _replace(stubs, "com/hbm/blockentity/LoadedBaseBlockEntity.java",
             "public float getVolume(float v){return v;}public void serialize(RegistryFriendlyByteBuf b){}public void deserialize(RegistryFriendlyByteBuf b){}",
             "public float getVolume(float v){return muffled?v*0.1F:v;}"
             "public void serialize(RegistryFriendlyByteBuf b){b.writeBoolean(muffled);b.writeBoolean(tilted);}"
             "public void deserialize(RegistryFriendlyByteBuf b){muffled=b.readBoolean();tilted=b.readBoolean();}")

    # ---- Cooling traits: production FT_Coolable on the Goal 9A FluidTrait/gson surface -----------------------------
    # The fluids and coolsTo products missing from the Goal 9A stand-in are appended (the earlier IDs stay) and get
    # the FT_Coolable traits parsed from production Fluids.java (steam: SPENTSTEAM, 100 mB -> 1 mB, 200 TU, TURBINE 1.0).
    fluids = stubs["com/hbm/inventory/fluid/Fluids.java"]
    existing = [(name, int(i), lead == "true", none == "true")
                for name, i, lead, none in re.findall(r"(\w+)=new FluidType\((\d+),(true|false),(true|false)\)", fluids)]
    statics = re.search(r"static\{(.*?)\}public static FluidType\[\] getAll", fluids).group(1)
    names = [name for name, *_ in existing]
    traits = coolable_traits(fluids_source)
    for fluid, product, *_ in traits:
        for name in (fluid, product):
            if name not in names:
                names.append(name)
                existing.append((name, len(existing), False, False))
    cool = "".join(
        f"{fluid}.addTraits(new com.hbm.inventory.fluid.trait.FT_Coolable({product},{req},{prod},{heat})"
        + "".join(f".setEff(com.hbm.inventory.fluid.trait.FT_Coolable.CoolingType.{kind},{eff}D)" for kind, eff in effs) + ");"
        for fluid, product, req, prod, heat, effs in traits)
    stubs["com/hbm/inventory/fluid/Fluids.java"] = (
        "package com.hbm.inventory.fluid;public class Fluids{public static final FluidType "
        + ",".join(f"{name}=new FluidType({i},{str(lead).lower()},{str(none).lower()})" for name, i, lead, none in existing)
        + ";static{" + statics + cool + "}public static FluidType[] getAll(){return new FluidType[]{" + ",".join(names) + "};}"
        + "public static FluidType fromID(int id){return switch(id){" + "".join(f"case {i}->{name};" for name, i, *_ in existing)
        + "default->NONE;};}public static FluidType fromNameCompat(String s){return NONE;}public static FluidType fromName(String s){return NONE;}}")
    return stubs
