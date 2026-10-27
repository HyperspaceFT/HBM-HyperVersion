package com.hbm.uninos.networkproviders;

import com.hbm.inventory.material.NTMMaterial;
import com.hbm.uninos.GenNode;
import com.hbm.uninos.INetworkProvider;
import com.hbm.util.fauxpointtwelve.DirPos;
import net.minecraft.core.BlockPos;

/** Upstream FoundryChannel.FoundryNode: a channel's node, carrying the material the channel currently holds. */
public class FoundryNode extends GenNode<FoundryNetwork> {

    public NTMMaterial type;

    public FoundryNode(INetworkProvider<FoundryNetwork> provider, BlockPos... positions) {
        super(provider, positions);
    }

    @Override
    public FoundryNode setConnections(DirPos... connections) {
        super.setConnections(connections);
        return this;
    }
}
