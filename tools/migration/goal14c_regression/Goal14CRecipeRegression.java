package com.hbm.inventory.recipes.loader;

import com.google.gson.*;
import com.google.gson.stream.JsonWriter;
import com.hbm.config.NtmConfig;
import com.hbm.inventory.RecipesCommon.*;
import com.hbm.inventory.MetaHelper;
import com.hbm.items.CastPlateItem;
import com.hbm.items.NtmItems;
import com.hbm.blocks.NtmBlocks;
import com.hbm.inventory.NtmTags;
import com.hbm.inventory.fluid.*;
import com.hbm.inventory.recipes.*;
import com.hbm.inventory.recipes.CompressorRecipes.*;
import com.hbm.handler.CompressorRecipeClientSync;
import com.hbm.main.NuclearTechMod;
import com.hbm.network.toclient.CompressorRecipesPacket;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.neoforged.neoforge.client.event.ClientPlayerNetworkEvent;
import net.neoforged.neoforge.event.OnDatapackSyncEvent;
import net.neoforged.neoforge.network.PacketDistributor;
import net.neoforged.neoforge.network.handling.IPayloadContext;
import java.nio.file.*;
import java.io.StringReader;
import java.io.StringWriter;
import java.util.*;

/** Actual compressor table, loader and public snapshot bridges; registry/transport services isolated. */
public class Goal14CRecipeRegression {
    static int checks, scenarios;
    static void check(boolean v,String m){if(!v)throw new AssertionError(m);checks++;}
    static void scenario(){scenarios++;}
    static String row(String input,String output,String duration){return "{\"recipes\":[{\"input\":"+input+",\"output\":"+output+(duration==null?"":",\"duration\":"+duration)+"}]}";}
    static final String CUSTOM=row("[\"PETROLEUM\",3000,1]","[\"LPG\",1500,0]","37");
    static void assembly(Path work)throws Exception{
        for(boolean mode:new boolean[]{false,true}){scenario();NtmConfig.COMMON.ENABLE_528.set(mode);GenericRecipes.clearPools();AssemblyMachineRecipes.INSTANCE.deleteRecipes();AssemblyMachineRecipes.INSTANCE.registerDefaults();var h=AssemblyMachineRecipes.INSTANCE;var r=h.recipeNameMap.get("ass.compressor");check(r!=null&&h.recipeOrderedList.stream().filter(v->v.name.equals("ass.compressor")).count()==1,"one actual normal compressor entry both528 "+mode);check(r.duration==200&&r.power==100&&!r.isPooled()&&r.inputItem.length==5&&r.outputItem.length==1,"assembly time/power/no blueprint gate");
            var plate=(ComparableStack)r.inputItem[0];check(plate.item==NtmItems.CAST_PLATE.get()&&plate.meta==CastPlateItem.Type.STEEL.ordinal()&&plate.stacksize==8,"8 steel cast plate actual META");var copper=(TagStack)r.inputItem[1];check(copper.tag.equals(NtmTags.Items.PLATES_COPPER)&&copper.stacksize==4,"4 copper plate tag");Object[][] fixed={{NtmItems.SHELL_STEEL.get(),2},{NtmItems.MOTOR.get(),3},{NtmItems.CIRCUIT_ANALOG_BOARD.get(),1}};for(int i=0;i<3;i++){var a=(ComparableStack)r.inputItem[i+2];check(a.item==fixed[i][0]&&a.stacksize==(int)fixed[i][1],"fixed assembly ingredient "+i);}var output=(GenericRecipes.ChanceOutput)r.outputItem[0];check(output.stack.getItem()==NtmBlocks.MACHINE_COMPRESSOR.asItem()&&output.stack.getCount()==1,"one compressor output");
            StringWriter s=new StringWriter();try(JsonWriter w=new JsonWriter(s)){w.beginObject().name("recipes").beginArray().beginObject();h.writeRecipe(r,w);w.endObject().endArray().endObject();}Files.writeString(work.resolve("assembly-reference-528-"+mode+".json"),s.toString());
            ChemicalPlantRecipes.INSTANCE.deleteRecipes();ChemicalPlantRecipes.INSTANCE.registerDefaults();var chemical=ChemicalPlantRecipes.INSTANCE.recipeNameMap.get("chem.deshcracked");check(chemical!=null&&ChemicalPlantRecipes.INSTANCE.recipeOrderedList.stream().filter(v->v.name.equals("chem.deshcracked")).count()==1&&chemical.duration==100&&chemical.power==100,"existing deshcracked exactly once unchanged");check(chemical.inputFluid[0].type==Fluids.LIGHTOIL_CRACK&&chemical.inputFluid[0].fill==500&&chemical.inputFluid[0].pressure==1&&chemical.inputFluid[1].type==Fluids.MERCURY&&chemical.inputFluid[1].fill==100,"existing pressured desh exact fluids");
        }NtmConfig.COMMON.ENABLE_528.set(false);
    }
    static void rejected(String text,String label){scenario();var before=new LinkedHashMap<>(CompressorRecipes.recipes);boolean failed=false;try{new CompressorRecipes().readRecipeStream(new StringReader(text));}catch(RuntimeException e){failed=true;}check(failed&&CompressorRecipes.recipes.equals(before),"atomic rejection "+label);}
    static void defaults(Path work)throws Exception{
        scenario();CompressorRecipes h=new CompressorRecipes();h.deleteRecipes();h.registerDefaults();
        check(CompressorRecipes.recipes.size()==5,"five special defaults");
        Object[][] rows={{Fluids.PETROLEUM,0,2000,Fluids.PETROLEUM,2000,1,20},{Fluids.PETROLEUM,1,2000,Fluids.LPG,1000,0,20},{Fluids.BLOOD,3,1000,Fluids.HEAVYOIL,250,0,200},{Fluids.PERFLUOROMETHYL,0,1000,Fluids.PERFLUOROMETHYL,1000,1,50},{Fluids.PERFLUOROMETHYL,1,1000,Fluids.PERFLUOROMETHYL_COLD,1000,0,50}};
        for(Object[] r:rows){scenario();CompressorRecipe v=CompressorRecipes.getRecipe((FluidType)r[0],(int)r[1]);check(v!=null&&v.inputAmount()==(int)r[2]&&v.outputType()==r[3]&&v.outputAmount()==(int)r[4]&&v.outputPressure()==(int)r[5]&&v.duration()==(int)r[6],"exact default "+r[0]+"/"+r[1]);}
        check(CompressorRecipes.getRecipe(Fluids.LIGHTOIL_CRACK,0)==null,"lightoil uses machine generic path");
        var defaults=new LinkedHashMap<>(CompressorRecipes.recipes);Path template=work.resolve("_hbmCompressor.json");h.writeTemplateFile(template.toFile());
        JsonArray written=JsonParser.parseString(Files.readString(template)).getAsJsonObject().getAsJsonArray("recipes");check(written.size()==5&&!written.toString().contains("hbmfluid."),"template precise internal names");
        for(JsonElement e:written)check(e.getAsJsonObject().has("duration"),"template duration explicit");
        h.deleteRecipes();h.readRecipeFile(template.toFile());check(CompressorRecipes.recipes.equals(defaults),"exact default duration template roundtrip");
        check(CompressorRecipes.readSnapshot(CompressorRecipes.writeSnapshot()).equals(defaults),"snapshot exact defaults");
        check(h.getFileName().equals("hbmCompressor.json"),"filename compatibility");
        SerializableRecipe.recipeHandlers.clear();SerializableRecipe.registerAllHandlers();check(SerializableRecipe.recipeHandlers.stream().filter(r->r instanceof CompressorRecipes).count()==1,"production register handler once");SerializableRecipe.recipeHandlers.clear();
    }
    static void disk(Path work)throws Exception{
        scenario();CompressorRecipes h=new CompressorRecipes();Path config=work.resolve("config");Files.createDirectories(config);NuclearTechMod.configDir=config.toFile();SerializableRecipe.recipeHandlers.clear();SerializableRecipe.recipeHandlers.add(h);SerializableRecipe.recipeSyncHandlers.clear();SerializableRecipe.initialize();check(CompressorRecipes.recipes.size()==5&&!h.modified,"missing disk defaults");
        Path file=config.resolve("hbmRecipes/hbmCompressor.json");Files.writeString(file,CUSTOM);SerializableRecipe.initialize();var v=CompressorRecipes.getRecipe(Fluids.PETROLEUM,1);check(h.modified&&CompressorRecipes.recipes.size()==1&&v.duration()==37&&v.inputAmount()==3000&&v.outputAmount()==1500,"custom full table replacement");
        scenario();Files.writeString(file,row("[\"PETROLEUM\",2000]","[\"LPG\",1000]",null));SerializableRecipe.initialize();check(CompressorRecipes.getRecipe(Fluids.PETROLEUM,0).duration()==100,"old missing duration means100");
        scenario();Files.writeString(file,row("[\"PETROLEUM\",2000]","[\"LPG\",1000]","0"));boolean rejected=false;try{SerializableRecipe.initialize();}catch(RuntimeException e){rejected=true;}check(rejected&&CompressorRecipes.recipes.isEmpty(),"legacy initializer deletes first then explicitly rejects invalid enabled file; no prior-table fallback");
        scenario();Files.writeString(file,"{\"recipes\":[]}");SerializableRecipe.initialize();check(CompressorRecipes.recipes.isEmpty()&&CompressorRecipes.getRecipe(Fluids.PETROLEUM,0)==null,"enabled empty table does not repopulate");
        scenario();SerializableRecipe.receiveRecipes(h.getFileName(),CUSTOM.getBytes(java.nio.charset.StandardCharsets.UTF_8));SerializableRecipe.initialize();check(CompressorRecipes.getRecipe(Fluids.PETROLEUM,1).duration()==37,"public legacy bridge custom duration");
        SerializableRecipe.receiveRecipes(h.getFileName(),"{\"recipes\":[]}".getBytes(java.nio.charset.StandardCharsets.UTF_8));SerializableRecipe.initialize();check(CompressorRecipes.recipes.isEmpty(),"public bridge empty replacement");SerializableRecipe.clearReceivedRecipes();check(CompressorRecipes.recipes.isEmpty(),"public clear restores empty disk table");
    }
    static void invalid(){
        new CompressorRecipes().readRecipeStream(new StringReader(CUSTOM));
        for(String duration:new String[]{"0","-1","1.5","1e2","\"100\"","2147483648","null","true"})rejected(row("[\"PETROLEUM\",2000]","[\"LPG\",1000]",duration),"duration "+duration);
        for(String input:new String[]{"[\"UNKNOWN\",1000]","[\"NONE\",1000]","[\"PETROLEUM\",0]","[\"PETROLEUM\",-1]","[\"PETROLEUM\",1.5]","[\"PETROLEUM\",1000,-1]","[\"PETROLEUM\",1000,5]","[\"PETROLEUM\",1000,\"1\"]","[\"PETROLEUM\",1000,1,1]"})rejected(row(input,"[\"LPG\",1000]","20"),"input "+input);
        for(String output:new String[]{"[\"UNKNOWN\",1000]","[\"NONE\",1000]","[\"LPG\",-1]","[\"LPG\",1e3]","[\"LPG\",1000,-1]","[\"LPG\",1000,6]"})rejected(row("[\"PETROLEUM\",1000]",output,"20"),"output "+output);
        rejected(CUSTOM.replace("]}",",{\"input\":[\"WATER\",0],\"output\":[\"LPG\",1]}]}"),"late row failure");
        String entry=JsonParser.parseString(CUSTOM).getAsJsonObject().getAsJsonArray("recipes").get(0).toString();rejected("{\"recipes\":["+entry+","+entry+"]}","duplicate valid key");
        rejected("{\"recipes\":["+String.join(",",Collections.nCopies(CompressorRecipes.MAX_SYNC_RECIPES+1,entry))+"]}","4097 rows bounded before publish");
        rejected("{\"recipes\":{}}","missing rows");rejected(" ".repeat(CompressorRecipes.MAX_SYNC_BYTES+1),"size bound stream parse");
        scenario();new CompressorRecipes().readRecipeStream(new StringReader(row("[\"WATER\",20000,4]","[\"WATER\",0,5]","1")));var v=CompressorRecipes.getRecipe(Fluids.WATER,4);check(v.inputAmount()==20000&&v.outputAmount()==0&&v.outputPressure()==5,"legal zero output and overcapacity do not increase machine capacity");
    }
    static void client()throws Exception{
        scenario();new CompressorRecipes().deleteRecipes();new CompressorRecipes().registerDefaults();var server=new LinkedHashMap<>(CompressorRecipes.recipes);String snapshot=CompressorRecipes.writeSnapshot();int[] refreshed={0};CompressorRecipeClientSync.setRefresh(()->refreshed[0]++);
        check(CompressorRecipeClientSync.getRecipes().equals(server)&&CompressorRecipeClientSync.getRecipes()!=CompressorRecipes.recipes,"client immutable independent defaults fallback");
        check(CompressorRecipeClientSync.receive(CUSTOM)&&refreshed[0]==1&&CompressorRecipeClientSync.getRecipe(Fluids.PETROLEUM,1).duration()==37,"client custom duration refresh");check(CompressorRecipes.recipes.equals(server),"integrated server isolation");
        boolean immutable=false;try{CompressorRecipeClientSync.getRecipes().clear();}catch(UnsupportedOperationException e){immutable=true;}check(immutable,"client immutable map");
        check(!CompressorRecipeClientSync.receive("invalid")&&!CompressorRecipeClientSync.receive(" ".repeat(CompressorRecipes.MAX_SYNC_BYTES+1))&&CompressorRecipeClientSync.getRecipe(Fluids.PETROLEUM,1).duration()==37&&refreshed[0]==1,"invalid/oversize retains prior snapshot");
        scenario();check(CompressorRecipeClientSync.receive("{\"recipes\":[]}")&&CompressorRecipeClientSync.getRecipes().isEmpty()&&CompressorRecipes.recipes.equals(server),"empty authoritative and isolated");
        CompressorRecipeClientSync.setRefresh(null);check(CompressorRecipeClientSync.receive(CUSTOM),"snapshot before JEI callback");int[] late={0};CompressorRecipeClientSync.setRefresh(()->late[0]++);check(CompressorRecipeClientSync.getRecipe(Fluids.PETROLEUM,1).duration()==37,"late JEI reads received table");
        var packet=new CompressorRecipesPacket(snapshot);var buf=new RegistryFriendlyByteBuf();CompressorRecipesPacket.STREAM_CODEC.encode(buf,packet);check(CompressorRecipesPacket.STREAM_CODEC.decode(buf).json().equals(snapshot),"actual codec roundtrip");CompressorRecipesPacket.handleCommon(packet,new IPayloadContext(){});check(CompressorRecipeClientSync.getRecipes().equals(server)&&late[0]==1,"actual handler queued receive");
        boolean huge=false;try{new CompressorRecipesPacket("中".repeat(CompressorRecipesPacket.MAX_BYTES/3+1));}catch(IllegalArgumentException e){huge=true;}check(huge,"packet bounds UTF8 bytes");
        new CompressorRecipes().deleteRecipes();CompressorRecipeClientSync.disconnect(new ClientPlayerNetworkEvent.LoggingOut());check(CompressorRecipeClientSync.getRecipes().size()==5&&late[0]==2,"disconnect restores defaults independent of server empty table");
        new CompressorRecipes().registerDefaults();Object a=new Object(),b=new Object();PacketDistributor.players.clear();PacketDistributor.packets.clear();CompressorRecipeSync.sync(new OnDatapackSyncEvent(List.of(a)));check(PacketDistributor.players.equals(List.of(a))&&PacketDistributor.packets.size()==1,"login only relevant player");
        PacketDistributor.players.clear();PacketDistributor.packets.clear();CompressorRecipeSync.sync(new OnDatapackSyncEvent(List.of(a,b)));check(PacketDistributor.players.equals(List.of(a,b))&&((CompressorRecipesPacket)PacketDistributor.packets.get(0)).json().equals(snapshot),"reload sends authoritative current memory");
    }
    public static void main(String[] args)throws Exception{Path work=Path.of(args[0]);assembly(work);defaults(work);disk(work);invalid();client();System.out.println("Goal14C actual recipe/loader/client/sync: "+checks+" checks; "+scenarios+" independent scenarios (no repeated ticks)");}
}
