package com.hbm.explosion.vanillant.standard;

import com.hbm.explosion.vanillant.ExplosionVNT;
import com.hbm.explosion.vanillant.interfaces.IExplosionSFX;
import com.hbm.network.toclient.AuxParticle;
import com.hbm.registry.NtmSoundEvents;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.level.Level;
import net.neoforged.neoforge.network.PacketDistributor;

/** Original ExplosionEffectTiny.java:14-26: the tiny explosion sound and one large explosion puff, sent within 100 blocks. */
public class ExplosionEffectTiny implements IExplosionSFX {

    @Override
    public void doEffect(ExplosionVNT explosion, Level level, double x, double y, double z, float size) {
        if(!(level instanceof ServerLevel serverLevel)) return;

        level.playSound(null, x, y, z, NtmSoundEvents.EXPLOSION_TINY.get(), SoundSource.BLOCKS, 15.0F, 1.0F);

        CompoundTag data = new CompoundTag();
        data.putString("type", "vanillaExt");
        data.putString("mode", "largeexplode");
        data.putFloat("size", 1.5F);
        data.putByte("count", (byte) 1);
        PacketDistributor.sendToPlayersNear(serverLevel, null, x, y, z, 100, new AuxParticle(data, x, y, z));
    }
}
