package com.hbm.inventory.recipes.loader;
import com.google.gson.*;
import com.google.gson.stream.JsonWriter;
import com.hbm.inventory.recipes.*;
import com.hbm.inventory.recipes.CentrifugeRecipes.CentrifugeRecipe;
import com.hbm.inventory.MetaHelper;
import com.hbm.items.component.NtmDataComponents;
import com.hbm.handler.CentrifugeRecipeClientSync;
import com.hbm.handler.jei.CentrifugeRecipeHandler;
import com.hbm.network.toclient.CentrifugeRecipesPacket;
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
public class Goal16BRecipeRegression {
 static int checks;
 static void check(boolean value,String name){checks++;if(!value)throw new AssertionError(name);}
 static void fails(Runnable action,String label){boolean failure=false;try{action.run();}catch(RuntimeException e){failure=true;}check(failure,label);}
 static String row(String input,String outputs){return "{\"input\":"+input+",\"outputs\":["+outputs+"]}";}
 static String table(String rows){return "{\"recipes\":["+rows+"]}";}
 static final String IN="[\"minecraft:blaze_rod\",1,null]", OUT="[\"minecraft:blaze_powder\",100,null]";
 static final String CUSTOM=table(row(IN,"[\"minecraft:air\",0],"+OUT));
 static void load(String json){new CentrifugeRecipes().readRecipeStream(new StringReader(json));}
 /** Invalid row: strict snapshot/sync parsing still throws without touching the table; the config-file load skips it and keeps the other rows. */
 static void reject(String json,String name)throws Exception{
  String before=CentrifugeRecipes.writeSnapshot();fails(()->CentrifugeRecipes.readSnapshot(json),name);check(before.equals(CentrifugeRecipes.writeSnapshot()),"atomic "+name);
  int rows=JsonParser.parseString(json).getAsJsonObject().getAsJsonArray("recipes").size();
  load(json);check(CentrifugeRecipes.getJeiRecipes().size()<rows,"file load skips invalid row "+name);CentrifugeRecipes.writeSnapshot();
  load(before);check(before.equals(CentrifugeRecipes.writeSnapshot()),"restore after "+name);
 }
 static void defaults(Path out)throws Exception{
  var handler=new CentrifugeRecipes();handler.deleteRecipes();handler.registerDefaults();
  var frozen=new FrozenCentrifugeRecipes();frozen.deleteRecipes();frozen.registerDefaults();
  var actual=CentrifugeRecipes.getJeiRecipes();var expected=FrozenCentrifugeRecipes.getJeiRecipes();
  check(actual.size()==76&&expected.size()==76,"full76");
  for(int i=0;i<76;i++){
   var a=actual.get(i);var e=expected.get(i);check(ItemStack.isSameItemSameComponents(a.input,e.input)&&a.input.getCount()==e.input.getCount(),"default input "+i);
   check(a.outputs.length==e.outputs.length,"default slot length "+i);
   for(int j=0;j<a.outputs.length;j++)check(a.outputs[j].getCount()==e.outputs[j].getCount()&&ItemStack.isSameItemSameComponents(a.outputs[j],e.outputs[j]),"default output "+i+":"+j);
   ItemStack natural=new ItemStack(a.input.getItem());check(CentrifugeRecipes.hasRecipe(natural),"natural input "+i);
  }
  String snapshot=CentrifugeRecipes.writeSnapshot();Files.writeString(out.resolve("defaults-snapshot.json"),snapshot);
  handler.writeTemplateFile(out.resolve("_hbmCentrifuge.json").toFile());frozen.writeTemplateFile(out.resolve("_frozen-hbmCentrifuge.json").toFile());
  check(JsonParser.parseString(Files.readString(out.resolve("_hbmCentrifuge.json"))).getAsJsonObject().get("recipes").equals(JsonParser.parseString(snapshot).getAsJsonObject().get("recipes")),"production template writer matches canonical snapshot");
  load(snapshot);var round=CentrifugeRecipes.getJeiRecipes();for(int i=0;i<76;i++)check(actual.get(i).sameRecipe(round.get(i)),"all defaults writer roundtrip "+i);
  var copy=CentrifugeRecipes.getDefaultRecipes();copy.getFirst().outputs[0].setCount(999);check(CentrifugeRecipes.getDefaultRecipes().getFirst().outputs[0].getCount()!=999,"default defense");
  Files.writeString(out.resolve("default-comparison.json"),"{\"rows\":76,\"all_inputs_outputs_counts_components_order_equal_frozen_production_rows\":true,\"canonical_writer_roundtrip_all_rows\":true,\"legacy_frozen_writer\":\"_frozen-hbmCentrifuge.json\",\"intentional_schema\":\"null META preserves absent components; old writer omitted zero/absent metadata\"}");
 }
 static void config(Path out)throws Exception{
  load(CUSTOM);check(CentrifugeRecipes.getOutput(new ItemStack(Items.BLAZE_ROD))[1].getCount()==100,"over stack output retained");
  check(CentrifugeRecipes.getJeiRecipes().getFirst().outputs[0].isEmpty(),"AIR0 position");Files.writeString(out.resolve("custom-example.json"),CentrifugeRecipes.writeSnapshot());
  ItemStack copied=CentrifugeRecipes.getJeiRecipes().getFirst().input;copied.setCount(99);check(CentrifugeRecipes.getJeiRecipes().getFirst().input.getCount()==1,"authority copy");
  load(table(row("[\"minecraft:blaze_rod\",2147483647]","[\"minecraft:blaze_powder\",2147483647]")));check(CentrifugeRecipes.getJeiRecipes().getFirst().input.getCount()==1&&CentrifugeRecipes.getJeiRecipes().getFirst().outputs[0].getCount()==Integer.MAX_VALUE,"positive ints canonical input no output cutoff");
  for(String in:List.of("[\"unknown:no\"]","[\"minecraft:air\",0]","[\"minecraft:blaze_rod\",0]","[\"minecraft:blaze_rod\",-1]","[\"minecraft:blaze_rod\",1.5]","[\"minecraft:blaze_rod\",2147483648]","[\"minecraft:blaze_rod\",1,-1]","[\"minecraft:blaze_rod\",1,0,\"bad\"]"))reject(table(row(in,OUT)),"bad input "+in);
  for(String outputs:List.of("", "[\"minecraft:air\",0]", "[\"minecraft:blaze_powder\",0]", "[\"unknown:no\",1]",String.join(",",Collections.nCopies(5,OUT)),"null"))reject(table(row(IN,outputs)),"bad outputs "+outputs);
  reject(table(row(IN,OUT)+","+row(IN,OUT)),"duplicate");reject(table(row(IN,OUT)+","+row("[\"minecraft:blaze_rod\",1,null,\"{probe:7}\"]",OUT)),"generic/exact overlap");
  String exact="[\"minecraft:blaze_rod\",1,null,\"{probe:7}\"]";
  load(table(row(exact,OUT)+","+row(exact.replace("probe:7","probe:8"),OUT)));check(CentrifugeRecipes.getJeiRecipes().size()==2,"disjoint exact signatures");
  ItemStack bare=new ItemStack(Items.BLAZE_ROD), seven=bare.copy();TagsUtil.putCustomData(seven,net.minecraft.nbt.TagParser.parseTag("{probe:7}"));
  check(!CentrifugeRecipes.hasRecipe(bare)&&CentrifugeRecipes.hasRecipe(seven),"exact components matching");seven.set("extra",1);check(!CentrifugeRecipes.hasRecipe(seven),"extra components constrain exact");
  String before=CentrifugeRecipes.writeSnapshot();load(before);check(before.equals(CentrifugeRecipes.writeSnapshot()),"exact writer roundtrip");
  reject(table(row(exact,OUT)+","+row(exact.replace("null","32767"),OUT)),"wildcard exact overlap");
  load(table(row("[\"minecraft:blaze_rod\",1,32767,\"{probe:7}\"]",OUT)));seven.remove("extra");MetaHelper.setMeta(seven,3);check(CentrifugeRecipes.hasRecipe(seven),"exact wildcard ignores onlyMETA");
  load(table(row(IN,OUT)));TagsUtil.putCustomData(bare,net.minecraft.nbt.TagParser.parseTag("{probe:9}"));check(CentrifugeRecipes.hasRecipe(bare),"legacy generic ignores custom data");
  for(String meta:List.of("0","null","32767")){load(table(row("[\"minecraft:blaze_rod\",2,"+meta+",\"{probe:7}\"]",OUT)));var r=CentrifugeRecipes.getJeiRecipes().getFirst();before=CentrifugeRecipes.writeSnapshot();load(before);check(r.sameRecipe(CentrifugeRecipes.getJeiRecipes().getFirst()),"META presence roundtrip "+meta);}
  String components=table(row(IN,"[\"minecraft:air\",0],[\"minecraft:blaze_powder\",2,null,\"{probe:7}\"],[\"minecraft:blaze_powder\",3,0,\"{probe:8}\"],[\"minecraft:blaze_powder\",4,null,\"{probe:7}\"]"));
  load(components);var ordered=CentrifugeRecipes.getJeiRecipes().getFirst();before=CentrifugeRecipes.writeSnapshot();load(before);check(ordered.sameRecipe(CentrifugeRecipes.getJeiRecipes().getFirst()),"four slots distinct components repeated outputs full roundtrip");
  String changed=components.replace("probe:7","probe:9");load(changed);check(!ordered.sameRecipe(CentrifugeRecipes.getJeiRecipes().getFirst()),"component difference row identity");
  var swapped=ordered.outputs.clone();ItemStack temporary=swapped[1];swapped[1]=swapped[2];swapped[2]=temporary;check(!ordered.sameRecipe(new CentrifugeRecipe(ordered.input,swapped)),"output order row identity");
  reject(table(row(IN,OUT)+","+row("[\"unknown:no\"]",OUT)),"later invalid row no early publication");
  load(table(row("[\"minecraft:blaze_rod\"]","[\"minecraft:blaze_powder\"]")));check(CentrifugeRecipes.getJeiRecipes().getFirst().input.has(NtmDataComponents.META.get())&&CentrifugeRecipes.getJeiRecipes().getFirst().outputs[0].has(NtmDataComponents.META.get()),"legacy omitted META materializes zero");
  ItemStack unsupported=new ItemStack(Items.BLAZE_POWDER);unsupported.set("extra",1);fails(()->CentrifugeRecipes.setRecipe(new ItemStack(Items.BLAZE_ROD),unsupported),"unrepresentable components");
  load("{\"recipes\":[]}");check(!CentrifugeRecipes.hasRecipe(new ItemStack(Items.BLAZE_ROD)),"empty disables");
  var frozen=new FrozenCentrifugeRecipes();frozen.deleteRecipes();
  ItemStack zero=MetaHelper.newStack(Items.BLAZE_ROD,1,0),one=MetaHelper.newStack(Items.BLAZE_ROD,1,1),wild=MetaHelper.newStack(Items.BLAZE_ROD,1,32767);
  FrozenCentrifugeRecipes.setRecipe(zero,new ItemStack(Items.BLAZE_POWDER,11));FrozenCentrifugeRecipes.setRecipe(one,new ItemStack(Items.BLAZE_POWDER,22));
  load(table(row("[\"minecraft:blaze_rod\",1,0]","[\"minecraft:blaze_powder\",11,null]")+","+row("[\"minecraft:blaze_rod\",1,1]","[\"minecraft:blaze_powder\",22,null]")));
  check(FrozenCentrifugeRecipes.getOutput(wild)[0].getCount()==11&&CentrifugeRecipes.getOutput(wild)[0].getCount()==11,"historical candidatewild first row old/new");
  check(FrozenCentrifugeRecipes.getOutput(one)[0].getCount()==22&&CentrifugeRecipes.getOutput(one)[0].getCount()==22,"ordinary concrete meta distinct old/new");
  check(CentrifugeRecipes.getJeiRecipes().size()==2,"legitimate distinct concrete meta rows retained");
  new CentrifugeRecipes().deleteRecipes();
  var h=new CentrifugeRecipes();for(int i=0;i<4096;i++)h.readRecipe(JsonParser.parseString(row("[\"minecraft:blaze_rod\",1,"+i+"]",OUT)));check(CentrifugeRecipes.getJeiRecipes().size()==4096,"4096 rows");fails(()->h.readRecipe(JsonParser.parseString(row("[\"minecraft:blaze_rod\",1,4096]",OUT))),"4097 rows");
 }
 static void client(Path out)throws Exception{
  load(CUSTOM);String server=CentrifugeRecipes.writeSnapshot();CentrifugeRecipeClientSync.setRefresh(null);check(CentrifugeRecipeClientSync.getRecipes().size()==76,"independent defaults");
  check(CentrifugeRecipeClientSync.receive(CUSTOM),"snapshot beforeJEI");var bridge=new goal16b.JeiBridge();bridge.available();check(bridge.displayedCentrifugeRecipes.size()==1&&bridge.runtime.additions==1,"lateJEI");
  CentrifugeRecipeClientSync.receive(CUSTOM);check(bridge.runtime.additions==1,"sameJEI object reuse");CentrifugeRecipeClientSync.receive(CUSTOM.replace("100","101"));check(bridge.runtime.additions==2,"count changes JEI row");
  var cache=CentrifugeRecipeClientSync.getRecipes();cache.getFirst().outputs[1].setCount(9);check(CentrifugeRecipeClientSync.getRecipes().getFirst().outputs[1].getCount()==101,"client defense");
  for(String bad:List.of("bad", " ".repeat(262145),table(row(IN,"[\"unknown:no\"]"))))check(!CentrifugeRecipeClientSync.receive(bad)&&bridge.displayedCentrifugeRecipes.size()==1,"invalid keeps cache");
  check(CentrifugeRecipeClientSync.receive("{\"recipes\":[]}")&&bridge.displayedCentrifugeRecipes.isEmpty(),"empty authoritative JEI");check(CentrifugeRecipes.writeSnapshot().equals(server),"integrated server isolated");
  bridge.unavailable();CentrifugeRecipeClientSync.receive(CUSTOM);bridge.available();check(bridge.displayedCentrifugeRecipes.size()==1,"JEI reconnect");
  var packet=new CentrifugeRecipesPacket(CUSTOM);var buf=new RegistryFriendlyByteBuf();CentrifugeRecipesPacket.STREAM_CODEC.encode(buf,packet);check(CentrifugeRecipesPacket.STREAM_CODEC.decode(buf).json().equals(CUSTOM),"packet codec");CentrifugeRecipesPacket.handleCommon(packet,new IPayloadContext(){});
  String empty="{\"recipes\":[]}";check(CentrifugeRecipes.readSnapshot(empty+" ".repeat(262144-empty.length())).isEmpty(),"exactASCII bytes");fails(()->CentrifugeRecipes.readSnapshot(empty+" ".repeat(262145-empty.length())),"byte+1");
  String emoji="{\"ignored\":\"中😀\",\"recipes\":[]}";int remain=262144-emoji.getBytes(StandardCharsets.UTF_8).length;var unicode=new CentrifugeRecipesPacket(emoji+" ".repeat(remain));CentrifugeRecipesPacket.STREAM_CODEC.encode(buf,unicode);check(CentrifugeRecipesPacket.STREAM_CODEC.decode(buf).json().equals(unicode.json()),"nonBMP exactbytes");
  for(char c:List.of('\ud800','\udfff')){String invalid="{\"ignored\":\""+c+"\",\"recipes\":[]}";fails(()->new CentrifugeRecipesPacket(invalid),"surrogate constructor");fails(()->CentrifugeRecipes.readSnapshot(invalid),"surrogate parser");}
  buf.writeByteArray(new byte[]{(byte)0xff});fails(()->CentrifugeRecipesPacket.STREAM_CODEC.decode(buf),"malformedUTF8");buf.writeByteArray(new byte[262145]);fails(()->CentrifugeRecipesPacket.STREAM_CODEC.decode(buf),"oversizedwire");
  CentrifugeRecipesPacket.handleCommon(new CentrifugeRecipesPacket("bad"),new IPayloadContext(){});check(bridge.displayedCentrifugeRecipes.size()==1,"malformed handler cache");
  CentrifugeRecipeClientSync.disconnect(new ClientPlayerNetworkEvent.LoggingOut());check(CentrifugeRecipeClientSync.getRecipes().size()==76&&CentrifugeRecipes.writeSnapshot().equals(server),"logout independent defaults");
  Object a=new Object(),b=new Object();PacketDistributor.players.clear();PacketDistributor.packets.clear();CentrifugeRecipeSync.sync(new OnDatapackSyncEvent(List.of(a)));check(PacketDistributor.players.equals(List.of(a))&&((CentrifugeRecipesPacket)PacketDistributor.packets.getFirst()).json().equals(server),"login memory");
  Files.writeString(out.resolve("hbmCentrifuge.json"),empty);PacketDistributor.players.clear();PacketDistributor.packets.clear();CentrifugeRecipeSync.sync(new OnDatapackSyncEvent(List.of(a,b)));check(PacketDistributor.players.equals(List.of(a,b))&&((CentrifugeRecipesPacket)PacketDistributor.packets.getFirst()).json().equals(server),"reload resend memory no disk reload");
 }
 public static void main(String[] args)throws Exception{Path out=Path.of(args[0]);defaults(out);config(out);client(out);System.out.println("Goal16B recipes: "+checks+" assertions; actual production parser/writer/matching/snapshot/client/packet/sync and extracted unchanged JEI refresh; frozen production default comparison; isolated services, not gameplay/save/server/JEI runtime.");}
}