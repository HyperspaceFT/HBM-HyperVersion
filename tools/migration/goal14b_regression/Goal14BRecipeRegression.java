package com.hbm.inventory.recipes.loader;

import com.google.gson.*;
import com.hbm.inventory.FluidStack;
import com.hbm.inventory.fluid.*;
import com.hbm.inventory.recipes.FractionRecipes;
import com.hbm.main.NuclearTechMod;
import com.hbm.handler.FractionRecipeClientSync;
import com.hbm.inventory.recipes.FractionRecipeSync;
import com.hbm.network.toclient.FractionRecipesPacket;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.neoforged.neoforge.client.event.ClientPlayerNetworkEvent;
import net.neoforged.neoforge.event.OnDatapackSyncEvent;
import net.neoforged.neoforge.network.PacketDistributor;
import net.neoforged.neoforge.network.handling.IPayloadContext;
import com.hbm.util.Tuple.Pair;
import java.nio.file.*;
import java.util.*;

/** Complete production fraction table and loader; isolated registry services. */
public class Goal14BRecipeRegression {
    static int checks;
    static void check(boolean v,String m){if(!v)throw new AssertionError(m);checks++;}
    static String describe(){
        TreeMap<String,String> m=new TreeMap<>();
        FractionRecipes.fractions.forEach((k,v)->m.put(k.getInternalName(),v.getKey().type.getInternalName()+":"+v.getKey().fill+":"+v.getKey().pressure+"/"+v.getValue().type.getInternalName()+":"+v.getValue().fill+":"+v.getValue().pressure));
        return m.toString();
    }
    static final String[][] ROWS={
        {"HEAVYOIL","BITUMEN","30","SMEAR","70"},{"HEAVYOIL_VACUUM","SMEAR","40","HEATINGOIL_VACUUM","60"},
        {"SMEAR","HEATINGOIL","60","LUBRICANT","40"},{"NAPHTHA","HEATINGOIL","40","DIESEL","60"},
        {"NAPHTHA_DS","XYLENE","60","DIESEL_REFORM","40"},{"NAPHTHA_CRACK","HEATINGOIL","30","DIESEL_CRACK","70"},
        {"LIGHTOIL","DIESEL","40","KEROSENE","60"},{"LIGHTOIL_DS","DIESEL_REFORM","60","KEROSENE_REFORM","40"},
        {"LIGHTOIL_CRACK","KEROSENE","70","PETROLEUM","30"},{"COALOIL","COALGAS","30","OIL","70"},
        {"COALCREOSOTE","COALOIL","10","BITUMEN","90"},{"REFORMATE","AROMATICS","40","XYLENE","60"},
        {"LIGHTOIL_VACUUM","KEROSENE","70","REFORMGAS","30"},{"EGG","CHOLESTEROL","50","RADIOSOLVENT","50"},
        {"OIL_COKER","CRACKOIL","30","HEATINGOIL","70"},{"NAPHTHA_COKER","NAPHTHA_CRACK","75","LIGHTOIL_CRACK","25"},
        {"GAS_COKER","AROMATICS","25","CARBONDIOXIDE","75"},{"CHLOROCALCITE_MIX","CHLOROCALCITE_CLEANED","50","COLLOID","50"},
        {"BAUXITE_SOLUTION","REDMUD","50","SODIUM_ALUMINATE","50"}
    };
    static final String CUSTOM="{\"recipes\":[{\"input\":\"NAPHTHA\",\"output1\":[\"HEATINGOIL\",13,2],\"output2\":[\"DIESEL\",87,3]}]}";
    public static void main(String[] args)throws Exception{
        Path work=Path.of(args[0]);FractionRecipes h=new FractionRecipes();h.deleteRecipes();h.registerDefaults();
        SerializableRecipe.recipeHandlers.clear();SerializableRecipe.registerAllHandlers();check(SerializableRecipe.recipeHandlers.stream().filter(r->r instanceof FractionRecipes).count()==1,"actual initializer registers fraction handler once");SerializableRecipe.recipeHandlers.clear();
        check(FractionRecipes.fractions.size()==19,"19 exact defaults");
        for(String[] row:ROWS){Pair<FluidStack,FluidStack> p=FractionRecipes.getFractions(Fluids.fromName(row[0]));check(p!=null&&p.getKey().type==Fluids.fromName(row[1])&&p.getKey().fill==Integer.parseInt(row[2])&&p.getValue().type==Fluids.fromName(row[3])&&p.getValue().fill==Integer.parseInt(row[4])&&p.getKey().pressure==0&&p.getValue().pressure==0,"exact default "+row[0]);}
        String defaults=describe();check(h.getFileName().equals("hbmFractions.json"),"fraction file identity");
        Path template=work.resolve("_hbmFractions.json");h.writeTemplateFile(template.toFile());
        JsonObject json=JsonParser.parseString(Files.readString(template)).getAsJsonObject();
        check(json.getAsJsonArray("recipes").size()==19,"template has all 19 entries");
        check(!json.toString().contains("hbmfluid."),"G11D internal names in template");
        h.deleteRecipes();h.readRecipeFile(template.toFile());check(describe().equals(defaults),"production template roundtrip");
        Path config=work.resolve("config");Files.createDirectories(config);NuclearTechMod.configDir=config.toFile();
        SerializableRecipe.recipeHandlers.clear();SerializableRecipe.recipeHandlers.add(h);SerializableRecipe.recipeSyncHandlers.clear();SerializableRecipe.initialize();
        check(describe().equals(defaults)&&!h.modified,"missing custom defaults");
        Path custom=config.resolve("hbmRecipes/hbmFractions.json");Files.writeString(custom,CUSTOM);SerializableRecipe.initialize();
        Pair<FluidStack,FluidStack> n=FractionRecipes.getFractions(Fluids.NAPHTHA);
        check(h.modified&&FractionRecipes.fractions.size()==1&&FractionRecipes.getFractions(Fluids.HEAVYOIL)==null,"custom replaces stale defaults");
        check(n.getKey().fill==13&&n.getKey().pressure==2&&n.getValue().fill==87&&n.getValue().pressure==3,"custom amounts and pressure");
        Files.writeString(custom,"{\"recipes\":[]}");SerializableRecipe.initialize();check(FractionRecipes.fractions.isEmpty(),"empty custom replaces stale table");
        SerializableRecipe.receiveRecipes(h.getFileName(),CUSTOM.getBytes(java.nio.charset.StandardCharsets.UTF_8));SerializableRecipe.initialize();
        check(FractionRecipes.fractions.size()==1&&FractionRecipes.getFractions(Fluids.NAPHTHA)!=null,"received table replaces empty custom");
        SerializableRecipe.receiveRecipes(h.getFileName(),"{\"recipes\":[]}".getBytes(java.nio.charset.StandardCharsets.UTF_8));SerializableRecipe.initialize();
        check(FractionRecipes.fractions.isEmpty(),"received empty clears stale entries");
        SerializableRecipe.clearReceivedRecipes();check(FractionRecipes.fractions.isEmpty(),"clear received restores empty disk table");
        Path fresh=work.resolve("fresh-config");Files.createDirectories(fresh);NuclearTechMod.configDir=fresh.toFile();SerializableRecipe.initialize();check(describe().equals(defaults),"defaults recover in fresh config");
        String snapshot=FractionRecipes.writeSnapshot();check(FractionRecipes.readSnapshot(snapshot).size()==19,"actual snapshot19 roundtrip");
        check(FractionRecipes.readSnapshot("{\"recipes\":[]}").isEmpty()&&describe().equals(defaults),"snapshot parse never clears server table");
        int[] refreshed={0};FractionRecipeClientSync.setRefresh(()->refreshed[0]++);
        check(FractionRecipeClientSync.getRecipes()==FractionRecipes.fractions,"client local fallback before receive");
        check(FractionRecipeClientSync.receive(CUSTOM)&&FractionRecipeClientSync.getRecipes().size()==1&&refreshed[0]==1,"client replacement refresh");
        check(describe().equals(defaults),"client snapshot isolated from integrated server");
        boolean immutable=false;try{FractionRecipeClientSync.getRecipes().clear();}catch(UnsupportedOperationException e){immutable=true;}check(immutable,"client snapshot map immutable");
        check(!FractionRecipeClientSync.receive("invalid")&&FractionRecipeClientSync.getRecipes().size()==1&&refreshed[0]==1,"invalid snapshot keeps prior no refresh");
        check(FractionRecipeClientSync.receive("{\"recipes\":[]}")&&FractionRecipeClientSync.getRecipes().isEmpty()&&refreshed[0]==2,"client empty snapshot clears stale");
        check(describe().equals(defaults),"client empty retains server defaults");
        FractionRecipeClientSync.disconnect(new ClientPlayerNetworkEvent.LoggingOut());check(FractionRecipeClientSync.getRecipes()==FractionRecipes.fractions&&refreshed[0]==3,"disconnect restores local refresh");
        var packet=new FractionRecipesPacket(CUSTOM);RegistryFriendlyByteBuf buf=new RegistryFriendlyByteBuf();FractionRecipesPacket.STREAM_CODEC.encode(buf,packet);check(FractionRecipesPacket.STREAM_CODEC.decode(buf).json().equals(CUSTOM),"packet UTF8 codec roundtrip");
        FractionRecipesPacket.handleCommon(packet,new IPayloadContext(){});check(FractionRecipeClientSync.getRecipes().size()==1&&refreshed[0]==4,"packet handler queued client replacement");
        boolean oversized=false;try{new FractionRecipesPacket("中".repeat(FractionRecipesPacket.MAX_BYTES/3+1));}catch(IllegalArgumentException e){oversized=true;}check(oversized,"packet bounds UTF8 bytes");
        check(!FractionRecipeClientSync.receive(" ".repeat(FractionRecipesPacket.MAX_BYTES+1))&&FractionRecipeClientSync.getRecipes().size()==1,"oversized receive preserves snapshot");
        Object a=new Object(),b=new Object();PacketDistributor.players.clear();PacketDistributor.packets.clear();FractionRecipeSync.sync(new OnDatapackSyncEvent(List.of(a)));check(PacketDistributor.players.equals(List.of(a))&&PacketDistributor.packets.size()==1,"login targets relevant player");
        PacketDistributor.players.clear();PacketDistributor.packets.clear();FractionRecipeSync.sync(new OnDatapackSyncEvent(List.of(a,b)));check(PacketDistributor.players.equals(List.of(a,b))&&((FractionRecipesPacket)PacketDistributor.packets.get(0)).json().equals(snapshot),"reload sends authoritative snapshot to relevant players");
        System.out.println("Goal14B actual fraction table/loader: "+checks+" checks passed");
    }
}
