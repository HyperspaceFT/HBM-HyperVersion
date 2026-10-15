"""Goal 19B stand-ins for the industrial steam turbine: the Goal 9B world unchanged, plus only what the turbine block entity needs.

Every change is an anchored replacement of a Goal 9B stand-in (the run stops if an anchor is missing or not unique), or a
whole-file replacement of a stand-in the Goal 9B world already declares (AudioWrapper). No stand-in may shadow a compiled
production source; verify_goal19b_machine.py checks that before compiling.
"""

from goal9b_regression.stubs import build_stubs as goal9b_stubs


def _replace(stubs, name, old, new):
    text = stubs.get(name)
    if text is None:
        raise SystemExit(f"Goal 19B stub file missing: {name}")
    if text.count(old) != 1:
        raise SystemExit(f"Goal 19B stub anchor in {name} found {text.count(old)} times (need 1): {old[:80]}")
    stubs[name] = text.replace(old, new)


def machine_stubs(source):
    stubs = goal9b_stubs(source)

    # ---- Registry entries (identities, as the Goal 9B world declares its own) --------------------------------------
    _replace(stubs, "com/hbm/blockentity/NtmBlockEntityTypes.java", "MACHINE_CONDENSER=new Ref()",
             "MACHINE_CONDENSER=new Ref(),MACHINE_INDUSTRIAL_TURBINE=new Ref()")
    _replace(stubs, "com/hbm/registry/NtmSoundEvents.java", "STEAM_ENGINE_OPERATE=new Ref()",
             "STEAM_ENGINE_OPERATE=new Ref(),TURBINE_LARGE_LOOP=new Ref()")

    # ---- Client player through the proxy -------------------------------------------------------------------------
    # Production ClientProxy.me() returns the client player and ServerProxy.me() null (NuclearTechMod.java:37,43);
    # the stand-in returns a settable player, null allowed.
    _replace(stubs, "com/hbm/main/NuclearTechMod.java",
             "public static class Proxy{public void openScreen(Player p,BlockPos pos){}}",
             "public static class Proxy{public void openScreen(Player p,BlockPos pos){}public Player client;public Player me(){return client;}}")
    # Vanilla 1.21.1 Entity.distanceToSqr(double, double, double): d0 = getX() - x, ...; d0*d0 + d1*d1 + d2*d2.
    # The Goal 9B Player stand-in returns 0 for getX/getY/getZ, so the position lives in its own fields.
    _replace(stubs, "net/minecraft/world/entity/player/Player.java",
             "public double distanceToSqr(double x,double y,double z){return 0;}",
             "public double atX,atY,atZ;public double distanceToSqr(double x,double y,double z){double d0=atX-x;double d1=atY-y;double d2=atZ-z;return d0*d0+d1*d1+d2*d2;}")

    # ---- Recording AudioWrapper ----------------------------------------------------------------------------------
    # Replaces the Goal 9B no-op stand-in (precedent goal13a_regression/stubs.py:149-156). Keeps the Goal 9B
    # BlockEntity overload and adds the production float-position overload the turbine uses
    # (AudioWrapper.java:42-46: event, source, x, y, z, volume, range, pitch, keepAlive). Every loop is recorded.
    old_audio = stubs.get("com/hbm/sound/AudioWrapper.java", "")
    if "getLoopedSound(Object e,Object c,Object be,float a,float b,float d,int f)" not in old_audio:
        raise SystemExit("Goal 19B: the Goal 9B AudioWrapper stand-in changed; review the recording replacement")
    stubs["com/hbm/sound/AudioWrapper.java"] = (
        "package com.hbm.sound;/** Goal 19B: records every loop the sources create (parameters, start/stop/keep-alive counts, last pitch and volume). */\n"
        "public class AudioWrapper{public static final java.util.List<AudioWrapper> CREATED=new java.util.ArrayList<>();"
        "public final Object event,source,be;public final float x,y,z,volume,range,pitch;public final int keepAlive;"
        "public int started,stopped,keptAlive,pitchUpdates,volumeUpdates;public float lastPitch=Float.NaN,lastVolume=Float.NaN;"
        "private AudioWrapper(Object e,Object s,Object be,float x,float y,float z,float v,float r,float p,int k){event=e;source=s;this.be=be;this.x=x;this.y=y;this.z=z;volume=v;range=r;pitch=p;keepAlive=k;}"
        "public static AudioWrapper getLoopedSound(Object e,Object c,Object be,float a,float b,float d,int f){AudioWrapper w=new AudioWrapper(e,c,be,Float.NaN,Float.NaN,Float.NaN,a,b,d,f);CREATED.add(w);return w;}"
        "public static AudioWrapper getLoopedSound(Object e,net.minecraft.sounds.SoundSource c,float x,float y,float z,float v,float r,float p,int k){AudioWrapper w=new AudioWrapper(e,c,null,x,y,z,v,r,p,k);CREATED.add(w);return w;}"
        "public void startSound(){started++;}public boolean isPlaying(){return started>0&&stopped==0;}public void keepAlive(){keptAlive++;}"
        "public void updatePitch(float p){pitchUpdates++;lastPitch=p;}public void updateVolume(float v){volumeUpdates++;lastVolume=v;}public void stopSound(){stopped++;}}")
    return stubs
