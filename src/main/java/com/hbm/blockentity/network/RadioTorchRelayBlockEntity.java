package com.hbm.blockentity.network;

import com.hbm.blockentity.ITickable;
import com.hbm.blockentity.LoadedBaseBlockEntity;
import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.blockentity.network.RTTYSystem.RTTYChannel;
import com.hbm.interfaces.IControlReceiver;
import com.hbm.util.Calculator;
import net.minecraft.core.BlockPos;
import net.minecraft.core.HolderLookup;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.block.state.BlockState;

import java.util.ArrayList;
import java.util.List;

/**
 * RoR calculation relay: listens to every channel named as {@code $name$} in its expression, evaluates the expression with the
 * received values and broadcasts the result on its own channel. Original TileEntityRadioTorchRelay.java.
 * Not a {@link RadioTorchBaseBlockEntity}: it has no mapping and syncs the expression and a double state instead.
 */
public class RadioTorchRelayBlockEntity extends LoadedBaseBlockEntity implements ITickable, IControlReceiver {

    /** Longest expression, the relay screen's text box limit (original GUIScreenRadioTorchRelay.java:59) */
    public static final int MAX_EXPRESSION_LENGTH = 100;

    /** Set by a new channel or expression and, as in the original (:105,112), never cleared: from then on every tick re-evaluates */
    public boolean forceUpdate = false;
    public boolean polling = false;
    public String channel = "";
    public String expression = "";
    /** last received value per listened channel */
    public CompoundTag variables = new CompoundTag();
    public double lastState = 0D;

    public RadioTorchRelayBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.RADIO_TORCH_RELAY.get(), pos, state);
    }

    @Override
    public void updateEntity() {
        if(this.level == null || this.level.isClientSide) return;

        if(!this.expression.isEmpty() && !this.channel.isEmpty()) {
            boolean sendUpdate = false;

            for(String freq : new ArrayList<>(this.variables.getAllKeys())) {

                RTTYChannel chan = RTTYSystem.listen(this.level, freq);
                if(chan == null) continue;

                String rec = "" + chan.signal;

                if(this.polling || this.forceUpdate || !rec.equals(this.variables.getString(freq))) {
                    if(this.polling && chan.timeStamp < this.level.getGameTime() - 1) rec = "0";
                    this.variables.putString(freq, rec);
                    sendUpdate = true;
                }
            }

            // if at least once value has changed, either through polling or actual state change, calculate and send the result
            if(sendUpdate) {
                // Intentional deviation: the original (:52) lets an evaluation exception escape the tile entity update. Here a
                // malformed expression or received value only skips this tick: nothing is broadcast and lastState keeps its value.
                try {
                    double result = Calculator.evaluateExpression(this.generateExpression());
                    this.lastState = result;
                    RTTYSystem.broadcast(this.level, this.channel, "" + result);
                } catch(Exception ignored) { }
            }
        }

        this.networkPackNT(15);
    }

    @Override
    public void serialize(RegistryFriendlyByteBuf buf) {
        buf.writeBoolean(this.polling);
        buf.writeUtf(this.channel);
        buf.writeUtf(this.expression);
        buf.writeDouble(this.lastState);
    }

    @Override
    public void deserialize(RegistryFriendlyByteBuf buf) {
        this.polling = buf.readBoolean();
        this.channel = buf.readUtf();
        this.expression = buf.readUtf();
        this.lastState = buf.readDouble();
    }

    @Override
    protected void loadAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.loadAdditional(tag, registries);

        this.polling = tag.getBoolean("p");
        this.channel = tag.getString("c");
        this.expression = tag.getString("e");
        this.lastState = tag.getDouble("l");
        this.variables = tag.getCompound("v");
    }

    @Override
    protected void saveAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.saveAdditional(tag, registries);

        tag.putBoolean("p", this.polling);
        tag.putString("c", this.channel);
        tag.putString("e", this.expression);
        tag.putDouble("l", this.lastState);
        tag.put("v", this.variables);
    }

    public void setChannel(String channel) {
        if(this.channel.equals(channel)) return;

        this.channel = channel;
        this.forceUpdate = true;
    }

    public void setExpression(String expression) {
        if(this.expression.equals(expression)) return;

        this.expression = expression;
        this.forceUpdate = true;

        this.variables = new CompoundTag();

        List<String> vars = this.getVariablesFromExpression();
        for(String var : vars) this.variables.putString(var, "");
    }

    @Override
    public boolean hasPermission(Player player) {
        // original :121-123: closer than 16 blocks to the block centre
        return player.distanceToSqr(worldPosition.getX() + 0.5D, worldPosition.getY() + 0.5D, worldPosition.getZ() + 0.5D) < 16D * 16D;
    }

    @Override
    public void receiveControl(CompoundTag data) {
        if(data.contains("p")) this.polling = data.getBoolean("p");
        // the screen's text boxes stop at these lengths; longer input only comes from a modified client and is cut here
        if(data.contains("e")) this.setExpression(RadioTorchBaseBlockEntity.truncate(data.getString("e"), MAX_EXPRESSION_LENGTH));
        if(data.contains("c")) this.setChannel(RadioTorchBaseBlockEntity.truncate(data.getString("c"), RadioTorchBaseBlockEntity.MAX_CHAN_LENGTH));

        this.setChanged();
    }

    /** Substitutes all varnames with the actual variable values */
    public String generateExpression() {
        if(!this.expression.contains("$")) return this.expression;

        StringBuilder joined = new StringBuilder();
        StringBuilder var = new StringBuilder();
        boolean readingVar = false;

        for(char c : this.expression.toCharArray()) {

            if(c == '$') {
                if(!readingVar) {
                    readingVar = true;
                } else {
                    String varName = var.toString();
                    String variable = this.variables.getString(varName);
                    if(variable.isEmpty()) variable = "0";
                    joined.append(variable);
                    var.delete(0, var.length());
                    readingVar = false;
                }
            } else {
                if(readingVar) {
                    var.append(c);
                } else {
                    joined.append(c);
                }
            }
        }

        return joined.toString();
    }

    /** Extracts all the variable names from the current expression */
    public List<String> getVariablesFromExpression() {
        List<String> vars = new ArrayList<>();
        if(!this.expression.contains("$")) return vars;

        StringBuilder var = new StringBuilder();
        boolean readingVar = false;

        for(char c : this.expression.toCharArray()) {

            if(c == '$') {
                if(!readingVar) {
                    readingVar = true;
                } else {
                    vars.add(var.toString());
                    var.delete(0, var.length());
                    readingVar = false;
                }
            } else {
                if(readingVar) {
                    var.append(c);
                }
            }
        }

        return vars;
    }
}
