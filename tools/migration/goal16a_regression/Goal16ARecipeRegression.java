package com.hbm.inventory.recipes.loader;

import com.google.gson.*;
import com.hbm.inventory.*;
import com.hbm.inventory.fluid.*;
import com.hbm.inventory.recipes.*;
import com.hbm.inventory.recipes.MixerRecipes.MixerRecipe;
import com.hbm.items.NtmItems;
import com.hbm.items.component.NtmDataComponents;
import com.hbm.handler.MixerRecipeClientSync;
import com.hbm.handler.jei.MixingRecipeHandler;
import com.hbm.main.NuclearTechMod;
import com.hbm.network.toclient.MixerRecipesPacket;
import com.hbm.util.TagsUtil;
import net.minecraft.world.item.*;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.neoforged.neoforge.client.event.ClientPlayerNetworkEvent;
import net.neoforged.neoforge.event.OnDatapackSyncEvent;
import net.neoforged.neoforge.network.PacketDistributor;
import net.neoforged.neoforge.network.handling.IPayloadContext;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;

/** Production methods run over documented registry, component, event and JEI service replacements. */
public class Goal16ARecipeRegression {
    static int checks,scenarios;
    static void check(boolean condition,String name){checks++;if(!condition)throw new AssertionError(name);}
    static void scenario(){scenarios++;}
    static String group(String output,String variants){return "{\"outputType\":\""+output+"\",\"recipes\":["+variants+"]}";}
    static String table(String groups){return "{\"recipes\":["+groups+"]}";}
    static String variant(String duration,String amount,String inputs){return "{\"duration\":"+duration+",\"outputAmount\":"+amount+(inputs.isEmpty()?"":","+inputs)+"}";}
    static final String FLUID="\"input1\":[\"WATER\",1]";
    static final String SIMPLE=variant("1","1",FLUID);
    static final String CUSTOM=table(group("COOLANT",variant("17","19","\"solidInput\":[\"nbt\",\"minecraft:egg\",2,null,\"{probe:7}\"]")));
    static void load(String json){new MixerRecipes().readRecipeStream(new StringReader(json));}
    static void fails(Runnable action,String label){boolean failed=false;try{action.run();}catch(RuntimeException ex){failed=true;}check(failed,label);}
    /** Whole-file failures (size, count, malformed document) still abort the stream load; the table stays untouched. */
    static void rejectFile(String json,String label)throws Exception{String before=MixerRecipes.writeSnapshot();fails(()->load(json),label);check(MixerRecipes.writeSnapshot().equals(before),"atomic "+label);}
    /** Invalid group: strict snapshot/sync parsing still throws without touching the table; the config-file load skips it and keeps the other groups. */
    static void reject(String json,String label)throws Exception{
        String before=MixerRecipes.writeSnapshot();fails(()->MixerRecipes.readSnapshot(json),label);check(MixerRecipes.writeSnapshot().equals(before),"atomic "+label);
        int rows=JsonParser.parseString(json).getAsJsonObject().getAsJsonArray("recipes").size();
        load(json);check(MixerRecipes.recipes.size()<rows,"file load skips invalid group "+label);MixerRecipes.writeSnapshot();
        load(before);check(MixerRecipes.writeSnapshot().equals(before),"restore after "+label);
    }

    static void defaults(Path output)throws Exception{
        scenario();Fluids.initializeGoal15BFuels();MixerRecipes handler=new MixerRecipes();handler.deleteRecipes();handler.registerDefaults();
        String defaults=MixerRecipes.writeSnapshot();Files.writeString(output.resolve("defaults-snapshot.json"),defaults);
        check(MixerRecipes.recipes.size()==38&&MixerRecipes.recipes.values().stream().mapToInt(a->a.length).sum()==48,"38/48 source-backed comparison also performed by Python");
        var expected=JsonParser.parseString(Files.readString(output.resolve("original-mapping.json"))).getAsJsonObject();
        check(JsonParser.parseString(defaults).equals(expected),"every amount, duration, identity, component and ordered variant matches original mapping");
        handler.writeTemplateFile(output.resolve("_hbmMixer.json").toFile());
        check(JsonParser.parseString(Files.readString(output.resolve("_hbmMixer.json"))).getAsJsonObject().get("recipes").equals(expected.get("recipes")),"true template writer export");
        int combos=0;
        for(var entry:MixerRecipes.recipes.entrySet())for(var recipe:entry.getValue()){
            combos|=(recipe.input1()==null?0:1)|(recipe.input2()==null?0:2)|(recipe.solidInput()==null?0:4);
            check(recipe.processTime()>0&&recipe.output()>0,"default valid row "+entry.getKey().getInternalName());
            if(recipe.solidInput()!=null){var values=recipe.solidInput().extractForJEI();for(var stack:values){check(recipe.solidInput().matchesRecipe(stack,false),"default solid full count");if(stack.getCount()>1)check(!recipe.solidInput().matchesRecipe(stack.copyWithCount(stack.getCount()-1),false),"default solid short count");}}
        }
        check(combos==7,"all input families present");
        var fish=MixerRecipes.getOutput(Fluids.FISHOIL,0).solidInput();
        for(Item item:List.of(Items.COD,Items.SALMON,Items.TROPICAL_FISH,Items.PUFFERFISH))check(fish.matchesRecipe(new ItemStack(item),false),"four raw fish "+item);
        check(!fish.matchesRecipe(new ItemStack(Items.COOKED_COD),false)&&!fish.matchesRecipe(new ItemStack(Items.COOKED_SALMON),false),"cooked fish rejected");
        List<Item> tars=List.of(NtmItems.OIL_TAR_CRUDE.get(),NtmItems.OIL_TAR_CRACK.get(),NtmItems.OIL_TAR_WOOD.get(),NtmItems.OIL_TAR_COAL.get());
        RecipesCommon.TAG_MEMBERS.put("ntm:any_tars",tars);tars.forEach(i->i.tags.add("ntm:any_tars"));
        var tar=MixerRecipes.getOutput(Fluids.BITUMEN,0).solidInput();for(Item i:tars)check(tar.matchesRecipe(new ItemStack(i),false),"four tars");
        check(tar.extractForJEI().size()==4&&!tar.matchesRecipe(new ItemStack(NtmItems.OIL_WAX.get()),false),"tag excludes wax");
        var copies=MixerRecipes.getOutput(Fluids.SOLVENT);copies[0]=null;check(MixerRecipes.getOutput(Fluids.SOLVENT,0)!=null,"array defense");
        var rec=MixerRecipes.getOutput(Fluids.SOLVENT,0);rec.input1().fill=0;check(rec.input1().fill==500,"fluid defense");
        check(MixerRecipes.getOutput(Fluids.NONE).length==0&&MixerRecipes.getOutput(Fluids.NONE,-1)==null,"absent group safe");
        check(MixerRecipes.getOutput(Fluids.SOLVENT,-1).input1().type==Fluids.NAPHTHA_COKER,"floorMod negative");
        check(MixerRecipes.getOutput(Fluids.SOLVENT,Integer.MIN_VALUE)!=null,"floorMod overflow boundary");
        SerializableRecipe.recipeHandlers.clear();SerializableRecipe.registerAllHandlers();check(SerializableRecipe.recipeHandlers.stream().filter(h->h instanceof MixerRecipes).count()==1,"one real loader registration");SerializableRecipe.recipeHandlers.clear();
    }

    static void config(Path output)throws Exception{
        scenario();Path dir=output.resolve("config");Files.createDirectories(dir);NuclearTechMod.configDir=dir.toFile();var handler=new MixerRecipes();SerializableRecipe.recipeHandlers.add(handler);SerializableRecipe.recipeSyncHandlers.clear();SerializableRecipe.initialize();
        check(MixerRecipes.recipes.size()==38&&!handler.modified,"loader default initialization");
        Path file=dir.resolve("hbmRecipes/hbmMixer.json");Files.writeString(file,CUSTOM);SerializableRecipe.initialize();check(handler.modified&&MixerRecipes.recipes.size()==1,"custom whole-table replacement");
        Files.writeString(output.resolve("custom-example.json"),MixerRecipes.writeSnapshot());
        for(int mask=1;mask<8;mask++){
            List<String> parts=new ArrayList<>();
            if((mask&1)!=0)parts.add("\"input1\":[\"WATER\",3]");
            if((mask&2)!=0)parts.add("\"input2\":[\"HYDROGEN\",5]");
            if((mask&4)!=0)parts.add("\"solidInput\":[\"item\",\"minecraft:egg\",2]");
            load(table(group("COOLANT",variant("7","11",String.join(",",parts)))));
            var combination=MixerRecipes.getOutput(Fluids.COOLANT,0);
            check((combination.input1()!=null)==((mask&1)!=0)&&(combination.input2()!=null)==((mask&2)!=0)&&(combination.solidInput()!=null)==((mask&4)!=0),"all seven input combinations "+mask);
        }
        Files.writeString(file,"{\"recipes\":[]}");SerializableRecipe.initialize();check(MixerRecipes.recipes.isEmpty(),"empty disk table disables");load(CUSTOM);
        for(String n:List.of("0","-1","1.5","1e2","\"1\"","2147483648","null","true")){
            reject(table(group("COOLANT",variant(n,"1",FLUID))),"duration "+n);
            reject(table(group("COOLANT",variant("1",n,FLUID))),"output "+n);
            reject(table(group("COOLANT",variant("1","1","\"input1\":[\"WATER\","+n+"]"))),"input "+n);
        }
        load(table(group("COOLANT",variant("2147483647","24000","\"input2\":[\"WATER\",16000]"))));check(MixerRecipes.getOutput(Fluids.COOLANT,0).processTime()==Integer.MAX_VALUE,"maximum positive int duration and capacity accepted");
        for(String fluid:List.of("[\"UNKNOWN\",1]","[\"NONE\",1]","[\"WATER\",16001]","[\"WATER\",1,1]","[\"WATER\",1,-1]","[\"WATER\",1,0,0]"))reject(table(group("COOLANT",variant("1","1","\"input1\":"+fluid))),"strict fluid "+fluid);
        reject(table(group("COOLANT",variant("1","24001",FLUID))),"output capacity");
        for(String name:List.of("NONE","UNKNOWN"))reject(table(group(name,SIMPLE)),"output identity");
        reject(table(group("COOLANT",variant("1","1",""))),"free output");reject(table(group("COOLANT","")),"empty group");
        reject(table(group("COOLANT",SIMPLE)+","+group("COOLANT",SIMPLE)),"duplicate group");
        reject(table(group("COOLANT",SIMPLE)+","+group("SOLVENT",variant("0","1",FLUID))),"late row cannot publish prefix");
        for(String solid:List.of("[\"item\",\"unknown:missing\"]","[\"item\",\"minecraft:air\"]","[\"item\",\"minecraft:egg\",0]","[\"item\",\"minecraft:egg\",65]","[\"tag\",\"unknown:missing\"]","[\"item\",\"minecraft:egg\",1,-1]","[\"nbt\",\"minecraft:egg\",1,null,\"broken\"]"))reject(table(group("COOLANT",variant("1","1","\"solidInput\":"+solid))),"strict solid "+solid);
        for(String solid:List.of("[\"item\",\"hbmsntm:fuel_additive\"]","[\"item\",\"hbmsntm:fuel_additive\",1,0]","[\"item\",\"hbmsntm:fuel_additive\",1,null]","[\"nbt\",\"hbmsntm:fuel_additive\",1,null,\"{}\"]","[\"nbt\",\"minecraft:egg\",2,0,\"{probe:7}\"]","[\"nbt\",\"minecraft:egg\",1,null,\"{}\"]")){
            load(table(group("COOLANT",variant("1","1","\"solidInput\":"+solid))));var before=MixerRecipes.getOutput(Fluids.COOLANT,0).solidInput().extractForJEI().getFirst();
            String snapshot=MixerRecipes.writeSnapshot();load(snapshot);var after=MixerRecipes.getOutput(Fluids.COOLANT,0).solidInput().extractForJEI().getFirst();
            check(ItemStack.isSameItemSameComponents(before,after)&&before.getCount()==after.getCount(),"META/custom roundtrip "+solid);
            var altered=after.copy();altered.set(NtmDataComponents.COLTAN_Z.get(),1);check(!MixerRecipes.getOutput(Fluids.COOLANT,0).solidInput().matchesRecipe(altered,true),"extra components mismatch");
            var leaked=MixerRecipes.getOutput(Fluids.COOLANT,0).solidInput();leaked.stacksize=63;check(MixerRecipes.getOutput(Fluids.COOLANT,0).solidInput().stacksize==before.getCount(),"solid defense");
        }
        load(CUSTOM);var exact=MixerRecipes.getOutput(Fluids.COOLANT,0).solidInput();check(!exact.matchesRecipe(new ItemStack(Items.EGG,2),false),"missing custom components rejects");
        JsonObject root=JsonParser.parseString(MixerRecipes.writeSnapshot()).getAsJsonObject();var recipe=MixerRecipes.getOutput(Fluids.COOLANT,0);var f=recipe.input1();
        fails(()->new MixerRecipe(1,1,null,null,new RecipesCommon.ComparableStack(Items.EGG)),"unsupported solid implementation rejected");
        var unsupported=new ItemStack(Items.EGG);unsupported.set(NtmDataComponents.COLTAN_Z.get(),4);
        var ctor=MixerRecipes.SolidInput.class.getDeclaredConstructor(List.class,net.minecraft.tags.TagKey.class,int.class);ctor.setAccessible(true);
        boolean refused=false;try{ctor.newInstance(List.of(unsupported),null,1);}catch(java.lang.reflect.InvocationTargetException ex){refused=ex.getCause() instanceof IllegalArgumentException;}
        check(refused,"production solid reconstruction rejects unrepresentable extra component");
        load(table(group("COOLANT",variant("1","1","\"solidInput\":[\"tag\",\"ntm:any_tars\"]"))));check(MixerRecipes.recipes.size()==1,"declared tag accepts before binding");
        RecipesCommon.TAG_MEMBERS.put("runtime:test",List.of(Items.EGG));load(table(group("COOLANT",variant("1","1","\"solidInput\":[\"tag\",\"runtime:test\"]"))));check(MixerRecipes.recipes.size()==1,"runtime bound tag accepts");
        load(table(group("COOLANT",SIMPLE)));reject(table(group("SOLVENT",String.join(",",Collections.nCopies(257,SIMPLE)))),"257 group variants");
        load(table(group("SOLVENT",String.join(",",Collections.nCopies(256,SIMPLE)))));check(MixerRecipes.getOutput(Fluids.SOLVENT).length==256,"256 group variants");
        rejectFile(table(String.join(",",Collections.nCopies(4097,group("COOLANT",SIMPLE)))),"4097 row bound");
        handler.deleteRecipes();var types=Arrays.stream(Fluids.getInNiceOrder()).filter(t->t!=Fluids.NONE).toList();
        for(int i=0;i<16;i++)handler.readRecipe(JsonParser.parseString(group(types.get(i).getInternalName(),String.join(",",Collections.nCopies(256,SIMPLE)))));
        check(MixerRecipes.recipes.values().stream().mapToInt(a->a.length).sum()==4096,"4096 total via direct production group parser");fails(()->handler.readRecipe(JsonParser.parseString(group(types.get(16).getInternalName(),SIMPLE))),"4097 total rejected");
        load(CUSTOM);rejectFile(" ".repeat(262145),"snapshot byte bound");rejectFile("中".repeat(87382),"UTF8 byte bound");
        String empty="{\"recipes\":[]}";
        check(MixerRecipes.readSnapshot(empty+" ".repeat(262144-empty.length())).isEmpty(),"exact 256KiB ASCII boundary accepted");
        String unicode="{\"comment\":\""+"中".repeat(87370)+"\",\"recipes\":[]}";
        int remaining=262144-unicode.getBytes(StandardCharsets.UTF_8).length;
        check(remaining>=0&&MixerRecipes.readSnapshot(unicode+" ".repeat(remaining)).isEmpty(),"exact 256KiB UTF8 boundary accepted");
        Files.writeString(file,table(group("COOLANT",variant("0","1",FLUID))));SerializableRecipe.initialize();check(handler.modified&&MixerRecipes.recipes.isEmpty(),"shared init skips the only bad disk group and keeps the cleared table, not claimed transactional");
        Files.writeString(file,table(group("COOLANT",SIMPLE)+","+group("SOLVENT",variant("0","1",FLUID))+","+group("WATER",SIMPLE)));SerializableRecipe.initialize();
        check(handler.modified&&MixerRecipes.recipes.size()==2&&MixerRecipes.getOutput(Fluids.COOLANT,0)!=null&&MixerRecipes.getOutput(Fluids.WATER,0)!=null&&MixerRecipes.getOutput(Fluids.SOLVENT,0)==null,"shared init skips only the bad middle group");
        for(String broken:List.of("{not json","{\"other\":[]}","","[]",table(String.join(",",Collections.nCopies(4097,group("COOLANT",SIMPLE)))),"{\"recipes\":["+group("COOLANT",SIMPLE)+"],\"comment\":\""+"x".repeat(262145)+"\"}")){
            Files.writeString(file,broken);SerializableRecipe.initialize();check(MixerRecipes.recipes.size()==38&&!handler.modified,"unusable disk file falls back to defaults without throwing");
        }
        Files.writeString(file,"{\"recipes\":[]}");SerializableRecipe.initialize();load(CUSTOM);
    }

    static void client(Path output)throws Exception{
        scenario();String server=MixerRecipes.writeSnapshot();MixerRecipeClientSync.setRefresh(null);check(MixerRecipeClientSync.getRecipes().size()==38,"independent defaults");
        check(MixerRecipeClientSync.receive(CUSTOM),"before JEI receive");var bridge=new goal16a.JeiBridge();bridge.available();check(bridge.displayedMixerRecipes.size()==1&&bridge.runtime.additions==1,"late JEI current snapshot");
        var row=MixingRecipeHandler.getRecipes().getFirst();check(row.sameRecipe(row),"actual category comparison");
        MixerRecipeClientSync.receive(CUSTOM);check(bridge.runtime.additions==1,"retained identical JEI object reused");
        String changed=CUSTOM.replace("probe:7","probe:8");MixerRecipeClientSync.receive(changed);check(!row.sameRecipe(MixingRecipeHandler.getRecipes().getFirst())&&bridge.runtime.additions==2,"JEI components change identity");
        String choices=table(group("COOLANT",variant("1","1","\"solidInput\":[\"any\",[\"item\",\"minecraft:cod\"],[\"item\",\"minecraft:salmon\"]]")));
        MixerRecipeClientSync.receive(choices);var ordered=MixingRecipeHandler.getRecipes().getFirst();
        MixerRecipeClientSync.receive(choices.replace("minecraft:cod","minecraft:TEMP").replace("minecraft:salmon","minecraft:cod").replace("minecraft:TEMP","minecraft:salmon"));
        check(!ordered.sameRecipe(MixingRecipeHandler.getRecipes().getFirst()),"JEI alternative display order participates in identity");
        MixerRecipeClientSync.receive(changed);
        for(String json:List.of("bad"," ".repeat(262145),table(group("UNKNOWN",SIMPLE))))check(!MixerRecipeClientSync.receive(json)&&MixingRecipeHandler.getRecipes().getFirst().recipe().solidInput().extractForJEI().getFirst().getCount()==2,"invalid cache kept");
        check(MixerRecipeClientSync.receive("{\"recipes\":[]}")&&bridge.displayedMixerRecipes.isEmpty(),"empty authoritative JEI hides rows");
        check(MixerRecipes.writeSnapshot().equals(server),"integrated server isolated");
        bridge.unavailable();check(MixerRecipeClientSync.receive(CUSTOM),"runtime unavailable noJEI bridge");bridge.available();check(bridge.displayedMixerRecipes.size()==1,"JEI reconnect");
        var clientCopy=MixerRecipeClientSync.getRecipes();clientCopy.get(Fluids.COOLANT)[0]=null;check(MixerRecipeClientSync.getRecipes().get(Fluids.COOLANT)[0]!=null,"client array defense");
        var packet=new MixerRecipesPacket(CUSTOM);var buf=new RegistryFriendlyByteBuf();MixerRecipesPacket.STREAM_CODEC.encode(buf,packet);check(MixerRecipesPacket.STREAM_CODEC.decode(buf).json().equals(CUSTOM),"production packet codec");MixerRecipesPacket.handleCommon(packet,new IPayloadContext(){});check(bridge.displayedMixerRecipes.size()==1,"queued production handler");
        fails(()->new MixerRecipesPacket("中".repeat(87382)),"packet UTF8 bound");buf.writeByteArray(new byte[262145]);fails(()->MixerRecipesPacket.STREAM_CODEC.decode(buf),"decode oversized length");
        for(char surrogate:new char[]{(char)0xd800,(char)0xdc00}){
            String invalid="{\"comment\":\""+surrogate+"\",\"recipes\":[]}";
            fails(()->new MixerRecipesPacket(invalid),"outgoing packet rejects unpaired surrogate "+Integer.toHexString(surrogate));
            fails(()->MixerRecipes.readSnapshot(invalid),"disk/snapshot rejects unpaired surrogate "+Integer.toHexString(surrogate));
        }
        String emoji="{\"comment\":\""+new String(Character.toChars(0x1f680)).repeat(65520)+"\",\"recipes\":[]}";
        emoji=emoji+" ".repeat(262144-emoji.getBytes(StandardCharsets.UTF_8).length);
        var emojiPacket=new MixerRecipesPacket(emoji);MixerRecipesPacket.STREAM_CODEC.encode(buf,emojiPacket);
        check(MixerRecipesPacket.STREAM_CODEC.decode(buf).json().equals(emoji)&&MixerRecipes.readSnapshot(emoji).isEmpty(),"valid nonBMP exact byte boundary and wire roundtrip");
        byte[] prefix="{\"ignored\":\"".getBytes(StandardCharsets.UTF_8),suffix="\",\"recipes\":[]}".getBytes(StandardCharsets.UTF_8);byte[] malformed=new byte[prefix.length+1+suffix.length];System.arraycopy(prefix,0,malformed,0,prefix.length);malformed[prefix.length]=(byte)0xff;System.arraycopy(suffix,0,malformed,prefix.length+1,suffix.length);buf.writeByteArray(malformed);fails(()->MixerRecipesPacket.STREAM_CODEC.decode(buf),"malformed UTF8 inside ignored JSON field");check(bridge.displayedMixerRecipes.size()==1,"invalid bytes cannot clear cache");
        MixerRecipesPacket.handleCommon(new MixerRecipesPacket("bad"),new IPayloadContext(){});check(bridge.displayedMixerRecipes.size()==1,"malformed snapshot preserves cache");
        MixerRecipeClientSync.disconnect(new ClientPlayerNetworkEvent.LoggingOut());check(MixerRecipeClientSync.getRecipes().size()==38&&MixerRecipes.writeSnapshot().equals(server),"disconnect independent fallback");
        Object a=new Object(),b=new Object();PacketDistributor.players.clear();PacketDistributor.packets.clear();MixerRecipeSync.sync(new OnDatapackSyncEvent(List.of(a)));check(PacketDistributor.players.equals(List.of(a))&&((MixerRecipesPacket)PacketDistributor.packets.getFirst()).json().equals(server),"login current memory");
        Files.writeString(output.resolve("config/hbmRecipes/hbmMixer.json"),"{\"recipes\":[]}");PacketDistributor.players.clear();PacketDistributor.packets.clear();MixerRecipeSync.sync(new OnDatapackSyncEvent(List.of(a,b)));check(PacketDistributor.players.equals(List.of(a,b))&&((MixerRecipesPacket)PacketDistributor.packets.getFirst()).json().equals(server),"reload resend without disk reread");
        bridge.unavailable();
    }
    public static void main(String[] args)throws Exception{Path out=Path.of(args[0]);defaults(out);config(out);client(out);System.out.println("Goal16A recipes: "+checks+" assertions, "+scenarios+" sections; production parser/writer/sync/JEI methods over isolated services; strict outgoing surrogate and incoming UTF8 boundaries covered");}
}
