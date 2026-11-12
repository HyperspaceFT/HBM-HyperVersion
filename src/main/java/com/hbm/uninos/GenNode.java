package com.hbm.uninos;

import com.hbm.util.fauxpointtwelve.DirPos;
import net.minecraft.core.BlockPos;

public class GenNode<N extends NodeNet> {
    public BlockPos[] positions;
    public DirPos[] connections;
    /** Quick reminder that this CAN and WILL be null for the first tick between the node being created
     * and the nodepsace update loop establishing a network. always check hasValidNet beforehand! */
    public N net;
    public boolean expired = false;
    public boolean recentlyChanged = true;
    /** Used for distinguishing the node type when saving it to UNINOS' node map */
    public INetworkProvider networkProvider;

    public GenNode(INetworkProvider<N> provider, BlockPos... positions) {
        this.networkProvider = provider;
        this.positions = positions;
    }

    public GenNode<N> setConnections(DirPos... connections) {
        this.connections = connections;
        return this;
    }

    public GenNode<N> addConnection(DirPos connection) {
        int length = this.connections == null ? 0 : this.connections.length;
        DirPos[] newCons = new DirPos[length + 1];
        for (int i = 0; i < length; i++) newCons[i] = this.connections[i];
        newCons[newCons.length - 1] = connection;
        this.connections = newCons;
        this.recentlyChanged = true;
        return this;
    }

    public boolean hasValidNet() {
        return this.net != null && this.net.isValid();
    }

    public void setNet(N net) {
        this.net = net;
        this.recentlyChanged = true;
    }
}
