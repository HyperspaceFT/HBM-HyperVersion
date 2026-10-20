package com.hbm.blockentity.machine.rbmk;

import com.hbm.handler.neutron.NeutronStream;

/**
 * Original com.hbm.tileentity.machine.rbmk.IRBMKFluxReceiver. The neutron types the fuel rods name came with Goal24B;
 * receiveFlux(NeutronStream) came with the neutron handler and the fuel column (Goal24C).
 */
public interface IRBMKFluxReceiver {

    enum NType {
        FAST("trait.rbmk.neutron.fast"),
        SLOW("trait.rbmk.neutron.slow"),
        ANY("trait.rbmk.neutron.any"); //not to be used for reactor flux calculation, only for the fuel designation

        public final String unlocalized;

        NType(String loc) {
            this.unlocalized = loc;
        }
    }

    void receiveFlux(NeutronStream stream);
}
