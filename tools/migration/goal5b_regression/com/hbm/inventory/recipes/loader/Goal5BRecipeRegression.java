package com.hbm.inventory.recipes.loader;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.google.gson.stream.JsonWriter;
import com.hbm.inventory.RecipesCommon.AStack;
import com.hbm.inventory.RecipesCommon.ComparableStack;
import com.hbm.inventory.recipes.PressRecipes;
import com.hbm.items.NtmItems;
import com.hbm.items.machine.StampItem;
import com.hbm.items.machine.StampItem.StampType;
import com.hbm.main.NuclearTechMod;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;

import java.io.StringWriter;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashSet;
import java.util.Set;

public class Goal5BRecipeRegression {
    private static int checks;
    private static void check(boolean value,String message){checks++;if(!value)throw new AssertionError(message);}
    private static ItemStack stamp(StampType type){return new ItemStack(new StampItem("stamp_"+type,type));}
    private static void expect(Item input,StampType type,Item output,int count){
        ItemStack actual=PressRecipes.getOutput(new ItemStack(input),stamp(type));
        check(actual.is(output)&&actual.getCount()==count,"live press recipe "+input.id+"/"+type+" -> "+output.id+" x"+count);
        check(PressRecipes.getInputCount(new ItemStack(input),stamp(type))==1,"default input count one for "+input.id);
    }
    public static void main(String[] args)throws Exception{
        Path config=Path.of(args[0]);NuclearTechMod.configDir=config.toFile();
        SerializableRecipe.recipeHandlers.clear();SerializableRecipe.recipeHandlers.add(new PressRecipes());
        SerializableRecipe.initialize();
        Path recipes=config.resolve("hbmRecipes");
        Path template=recipes.resolve("_hbmPress.json"),active=recipes.resolve("hbmPress.json");
        check(Files.isRegularFile(template)&&!Files.exists(active),"disabled underscore template exported without active file");
        Set<String> expected=Set.of("hbmsntm:coke_coal", "hbmsntm:coke_lignite", "hbmsntm:coke_petroleum", "hbmsntm:ingot_graphite");
        JsonArray exported=JsonParser.parseString(Files.readString(template)).getAsJsonObject().getAsJsonArray("recipes");
        JsonArray selected=new JsonArray();Set<String> seen=new HashSet<>();
        for(var raw:exported){
            JsonObject row=raw.getAsJsonObject();String id=row.getAsJsonArray("input").get(1).getAsString();
            if(expected.contains(id)){
                check(seen.add(id),"one exported default for "+id);
                check(row.getAsJsonArray("input").get(2).getAsInt()==1,"default consumes one "+id);
                check(row.getAsJsonArray("input").get(3).getAsInt()==32767,"default keeps wildcard input META");
                check(row.get("stamp").getAsString().equals(id.equals("hbmsntm:ingot_graphite")?"wire":"flat"),"default stamp for "+id);
                check(row.getAsJsonArray("output").get(0).getAsString().equals(id.equals("hbmsntm:ingot_graphite")?"hbmsntm:wire_carbon":"hbmsntm:ingot_graphite"),"default output ID for "+id);
                check(row.getAsJsonArray("output").size()>1 ? row.getAsJsonArray("output").get(1).getAsInt()==(id.equals("hbmsntm:ingot_graphite")?8:1) : !id.equals("hbmsntm:ingot_graphite"),"default output amount for "+id);
                selected.add(row);
            }
        }
        check(seen.equals(expected),"all four expected graphite/carbon-wire defaults exported");
        Path artifact=config.getParent().resolve("goal5b-press-defaults.json");
        // Export the selected live entries through PressRecipes.writeRecipe, not a handwritten formula.
        PressRecipes handler=new PressRecipes();StringWriter out=new StringWriter();JsonWriter writer=new JsonWriter(out);writer.setIndent("  ");writer.beginObject();writer.name("recipes").beginArray();
        int written=0;
        for(var entry:PressRecipes.recipes.entrySet()){
            AStack input=entry.getKey().getKey();
            if(input instanceof ComparableStack comparable&&expected.contains(comparable.item.id)){
                writer.beginObject();handler.writeRecipe(entry,writer);writer.endObject();written++;
            }
        }
        writer.endArray();writer.endObject();writer.close();
        Files.writeString(artifact,out.toString()+"\n",StandardCharsets.UTF_8);
        check(written==4&&JsonParser.parseString(Files.readString(artifact)).getAsJsonObject().getAsJsonArray("recipes").size()==4,
                "four actual writer objects saved for reviewed migration reference");
        expect(NtmItems.COKE_COAL.get(),StampType.FLAT,NtmItems.INGOT_GRAPHITE.get(),1);
        expect(NtmItems.COKE_LIGNITE.get(),StampType.FLAT,NtmItems.INGOT_GRAPHITE.get(),1);
        expect(NtmItems.COKE_PETROLEUM.get(),StampType.FLAT,NtmItems.INGOT_GRAPHITE.get(),1);
        expect(NtmItems.INGOT_GRAPHITE.get(),StampType.WIRE,NtmItems.WIRE_CARBON.get(),8);
        int defaultsSize=PressRecipes.recipes.size();SerializableRecipe.initialize();
        check(PressRecipes.recipes.size()==defaultsSize,"repeated default initialization does not duplicate recipes");

        String custom="{\"recipes\":[{\"input\":[\"item\",\"hbmsntm:coke_coal\",2,32767],\"stamp\":\"flat\",\"output\":[\"hbmsntm:ingot_graphite\",3]}]}";
        Files.writeString(active,custom,StandardCharsets.UTF_8);SerializableRecipe.initialize();
        check(Files.readString(active).equals(custom)&&PressRecipes.recipes.size()==1,
                "enabled custom file stays byte-identical and replaces defaults");
        check(PressRecipes.getOutput(new ItemStack(NtmItems.COKE_COAL.get(),1),stamp(StampType.FLAT)).isEmpty(),
                "custom count two rejects one coke");
        check(PressRecipes.getOutput(new ItemStack(NtmItems.COKE_COAL.get(),2),stamp(StampType.FLAT)).getCount()==3
                &&PressRecipes.getInputCount(new ItemStack(NtmItems.COKE_COAL.get(),2),stamp(StampType.FLAT))==2,
                "custom count and output amount respected");
        SerializableRecipe.initialize();
        check(PressRecipes.recipes.size()==1&&Files.readString(active).equals(custom),
                "repeated custom initialization neither duplicates nor rewrites file");
        String synced="{\"recipes\":[{\"input\":[\"item\",\"hbmsntm:coke_coal\",1,32767],\"stamp\":\"flat\",\"output\":[\"hbmsntm:ingot_graphite\",4]}]}";
        SerializableRecipe.receiveRecipes("hbmPress.json",synced.getBytes(StandardCharsets.UTF_8));
        SerializableRecipe.initialize();
        check(PressRecipes.getOutput(new ItemStack(NtmItems.COKE_COAL.get()),stamp(StampType.FLAT)).getCount()==4
                &&Files.readString(active).equals(custom),"received stream overrides active file in memory without rewriting it");
        SerializableRecipe.clearReceivedRecipes();
        check(PressRecipes.getOutput(new ItemStack(NtmItems.COKE_COAL.get(),2),stamp(StampType.FLAT)).getCount()==3
                &&Files.readString(active).equals(custom),"clearing sync restores active custom recipe");
        // Goal 11D: the production writer names a fluid by its internal name (the stand-in's "FLUID"), not by its language
        // key ("fluid"), as the original SerializableRecipe.java:424 writes getName().
        StringWriter fluidJson=new StringWriter();JsonWriter fluidWriter=new JsonWriter(fluidJson);
        SerializableRecipe.writeFluidStack(new com.hbm.inventory.FluidStack(com.hbm.inventory.fluid.Fluids.NONE,1_000),fluidWriter);fluidWriter.close();
        check(fluidJson.toString().equals("[\"FLUID\",1000]"),"Goal 11D: writeFluidStack writes the internal name: "+fluidJson);
        System.out.println("Goal 5B recipe checks: "+checks+"; artifact="+artifact);
    }
}
