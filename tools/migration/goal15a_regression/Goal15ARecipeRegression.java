package com.hbm.inventory.recipes.loader;
import com.google.gson.*;
import com.google.gson.stream.JsonWriter;
import com.hbm.config.NtmConfig;
import com.hbm.inventory.*;
import com.hbm.inventory.RecipesCommon.*;
import com.hbm.inventory.recipes.*;
import com.hbm.items.NtmItems;
import com.hbm.items.machine.PistonSetItem;
import com.hbm.blocks.NtmBlocks;
import net.minecraft.world.item.*;
import java.util.*;
import java.io.StringWriter;
import java.nio.file.*;

/** Actual assembly registration/writer against the frozen dirty-worktree baseline; identities isolated. */
public class Goal15ARecipeRegression {
    static int checks,scenarios;
    static void check(boolean v,String m){checks++;if(!v)throw new AssertionError(m);}
    static JsonObject write(GenericRecipes<GenericRecipe> h,GenericRecipe r)throws Exception{StringWriter s=new StringWriter();try(JsonWriter w=new JsonWriter(s)){w.beginObject();h.writeRecipe(r,w);w.endObject();}return JsonParser.parseString(s.toString()).getAsJsonObject();}
    static Map<String,JsonObject> catalog(GenericRecipes<GenericRecipe> h)throws Exception{h.deleteRecipes();h.registerDefaults();Map<String,JsonObject> m=new LinkedHashMap<>();for(var r:h.recipeOrderedList)m.put(r.name,write(h,r));return m;}
    static void fixed(GenericRecipe r,int index,Item item,int count,Integer meta){var a=(ComparableStack)r.inputItem[index];check(a.item==item&&a.stacksize==count,"fixed identity/count "+r.name+"/"+index);if(meta!=null){check(a.meta==meta,"fixed material component "+r.name+"/"+index);check(a.matchesRecipe(MetaHelper.newStack(item,count,meta),false)&&!a.matchesRecipe(MetaHelper.newStack(item,count,meta+1),false),"actual component matching rejects wrong material "+r.name+"/"+index);}ItemStack undersized=meta==null?new ItemStack(item,count-1):MetaHelper.newStack(item,count-1,meta);check(!a.matchesRecipe(undersized,false),"insufficient quantity with correct component refuses "+r.name+"/"+index);}
    static void tag(GenericRecipe r,int index,String id,int count){var a=(TagStack)r.inputItem[index];check(a.stacksize==count&&a.tag.location().toString().equals(id),"material tag/count "+r.name+"/"+index);}
    public static void main(String[] args)throws Exception{Path out=Path.of(args[0]);String[] newNames={"ass.combustiongen","ass.pistonsetsteel","ass.pistonsetdura","ass.pistonsetdesh"};JsonArray export=new JsonArray();
        for(boolean mode:new boolean[]{false,true}){scenarios++;NtmConfig.COMMON.ENABLE_528.set(mode);GenericRecipes.clearPools();var baseline=catalog(goal15a.base.AssemblyMachineRecipes.INSTANCE);var live=catalog(AssemblyMachineRecipes.INSTANCE);var retained=new LinkedHashMap<>(live);for(String n:newNames)retained.remove(n);check(retained.equals(baseline),"all previous recipes retain exact production writer contents both528 "+mode);check(new ArrayList<>(retained.keySet()).equals(new ArrayList<>(baseline.keySet())),"all previous recipe order retained both528 "+mode);check(live.size()==baseline.size()+4,"exactly4new assembly rows both528 "+mode);
            var h=AssemblyMachineRecipes.INSTANCE;for(int i=0;i<4;i++){scenarios++;var r=h.recipeNameMap.get(newNames[i]);check(r!=null&&h.recipeOrderedList.stream().filter(v->v.name.equals(r.name)).count()==1,"exactly one registered row "+newNames[i]);check(r.duration==(i==0?300:200)&&r.power==100&&!r.isPooled()&&r.getPools()==null&&r.outputItem.length==1,"normal duration/power/no blueprint "+r.name);var output=((GenericRecipes.ChanceOutput)r.outputItem[0]).stack;check(output.getCount()==1&&output.getItem()==(i==0?NtmBlocks.MACHINE_COMBUSTION_ENGINE.asItem():NtmItems.PISTON_SET.get()),"normal output identity "+r.name);if(i>0)check(MetaHelper.getMeta(output)==i-1,"piston output ordinal0/1/2 "+r.name);if(!mode)export.add(write(h,r));}
            var r=h.recipeNameMap.get(newNames[0]);check(r.inputItem.length==5,"engine5inputs");tag(r,0,"c:plates/steel",16);fixed(r,1,NtmItems.INGOT_COPPER.get(),12,null);fixed(r,2,NtmItems.WIRE_DENSE.get(),8,7900);fixed(r,3,NtmItems.CANISTER_EMPTY.get(),4,null);fixed(r,4,NtmItems.CIRCUIT_INTEGRATED_BOARD.get(),1,null);
            r=h.recipeNameMap.get(newNames[1]);check(r.inputItem.length==4,"steel4inputs");tag(r,0,"c:plates/steel",16);tag(r,1,"c:plates/copper",4);fixed(r,2,NtmItems.INGOT_TUNGSTEN.get(),8,null);fixed(r,3,NtmItems.BOLT.get(),16,7400);
            r=h.recipeNameMap.get(newNames[2]);check(r.inputItem.length==4,"Dura4inputs");fixed(r,0,NtmItems.INGOT_DURA_STEEL.get(),24,null);fixed(r,1,NtmItems.PLATE_TITANIUM.get(),8,null);fixed(r,2,NtmItems.INGOT_TUNGSTEN.get(),8,null);fixed(r,3,NtmItems.BOLT.get(),16,33);
            r=h.recipeNameMap.get(newNames[3]);check(r.inputItem.length==5,"Desh5inputs");fixed(r,0,NtmItems.INGOT_DESH.get(),24,null);tag(r,1,"ntm:ingots_plastic",12);tag(r,2,"c:plates/copper",24);fixed(r,3,NtmItems.INGOT_TUNGSTEN.get(),16,null);fixed(r,4,NtmItems.PIPE_DURA_STEEL.get(),4,null);
            h.deleteRecipes();for(String n:newNames){scenarios++;JsonObject before=live.get(n);h.readRecipe(before);check(write(h,h.recipeNameMap.get(n)).equals(before),"production writer/reader roundtrip "+n);}
            JsonObject rows=new JsonObject();rows.add("recipes",export);Files.writeString(out.resolve("assembly-reference-528-"+mode+".json"),rows.toString());
        }NtmConfig.COMMON.ENABLE_528.set(false);JsonObject result=new JsonObject();result.add("recipes",export);Files.writeString(out.resolve("goal15a-assembly-recipes.json"),result.toString());System.out.println("Goal15A actual recipe registration/writer/component matching: "+checks+" assertions; "+scenarios+" independent scenarios; both528 settings; frozen old table retained");
    }
}
