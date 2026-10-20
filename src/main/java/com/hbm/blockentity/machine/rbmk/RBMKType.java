package com.hbm.blockentity.machine.rbmk;

/** Original RBMKNeutronHandler.RBMKType (:28-36): how a column takes part in the neutron calculation. */
public enum RBMKType {
    ROD,
    MODERATOR,
    CONTROL_ROD,
    REFLECTOR,
    ABSORBER,
    OUTGASSER,
    OTHER // why do neutron calculations on them if they won't change anything?
}
