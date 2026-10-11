package com.hbm.blockentity.machine;

import com.hbm.handler.jei.CrucibleCastingRecipeHandler;
import com.hbm.inventory.material.Mats;
import com.hbm.inventory.material.Mats.MaterialStack;
import com.hbm.inventory.recipes.anvil.AnvilSmithingBladeMoldRecipe;
import com.hbm.items.NtmItems;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.HitResult;
import java.util.ArrayList;
import java.util.List;
import mezz.jei.api.gui.builder.*;
import mezz.jei.api.gui.drawable.IDrawable;
import mezz.jei.api.helpers.IGuiHelper;
import mezz.jei.api.recipe.RecipeIngredientRole;
import net.minecraft.resources.ResourceLocation;

public final class Goal17AAcquisitionRegression {
    private static int checks;
    private static void check(boolean value, String message) {
        checks++;
        if(!value) throw new AssertionError(message);
    }
    private static Level level() { Level l = new Level(); l.manualClock = true; return l; }
    private static FoundryMoldBlockEntity mold(Level l, int x) {
        FoundryMoldBlockEntity m = new FoundryMoldBlockEntity(new BlockPos(x,0,0), new BlockState());
        l.put(m); return m;
    }
    private static FoundryMoldBlockEntity blade(Level l, int x) {
        FoundryMoldBlockEntity m = mold(l,x);
        check(m.insertMold(new ItemStack(NtmItems.MOLD_BLADE.get()).component("mold-components")), "insert reusable blade mold");
        return m;
    }
    private static void smithing() {
        AnvilSmithingBladeMoldRecipe r = new AnvilSmithingBladeMoldRecipe();
        check(r.getTier()==1 && !r.isShapeless(), "ordered tier one");
        check(r.getLeft().size()==2 && r.getLeft().get(0).is(NtmItems.BLADE_TITANIUM.get()) && r.getLeft().get(1).is(NtmItems.BLADE_TUNGSTEN.get()), "both actual blade samples displayed");
        for(var item : List.of(NtmItems.BLADE_TITANIUM.get(),NtmItems.BLADE_TUNGSTEN.get())) {
            ItemStack sample = new ItemStack(item).component("sample-components");
            ItemStack blanks = new ItemStack(NtmItems.MOLD_BASE.get(),3).component("blank-components");
            for(int i=0;i<3;i++) {
                check(r.matchesInt(sample,blanks)==0, "sample reusable with multiple blanks");
                check(r.getOutput(sample,blanks).is(NtmItems.MOLD_BLADE.get()), "new mold output");
                sample.shrink(r.amountConsumed(0,false)); blanks.shrink(r.amountConsumed(1,false));
                check(sample.getCount()==1 && sample.component().equals("sample-components"), "sample count/components untouched");
            }
            check(blanks.isEmpty() && r.matchesInt(sample,blanks)==-1, "exactly one blank consumed per mold");
            check(r.matchesInt(new ItemStack(item,2),new ItemStack(NtmItems.MOLD_BASE.get()))==-1, "two samples reject");
            check(r.matchesInt(new ItemStack(NtmItems.MOLD_BASE.get()),sample)==-1, "mirror rejects");
        }
        check(r.matchesInt(ItemStack.EMPTY,new ItemStack(NtmItems.MOLD_BASE.get()))==-1, "empty sample rejects");
        check(r.matchesInt(new ItemStack(NtmItems.INGOT_DURA_STEEL.get()),new ItemStack(NtmItems.MOLD_BASE.get()))==-1, "wrong sample rejects");
        check(r.amountConsumed(0,true)==0 && r.amountConsumed(1,true)==0, "invalid mirrored consumption zero");
    }
    private static void bounds() {
        Level l=level(); FoundryMoldBlockEntity empty=mold(l,0);
        check(empty.pour(new MaterialStack(Mats.MAT_TUNGSTEN,216))==0,"no mold rejects");
        FoundryMoldBlockEntity m=blade(l,1);
        check(m.getCapacity()==216,"3 ingots capacity");
        for(var mat : List.of(Mats.MAT_DURA,Mats.MAT_STEEL,Mats.MAT_COPPER,Mats.MAT_COBALT)) check(m.pour(new MaterialStack(mat,216))==0,"non tungsten rejects");
        check(m.pour(null)==0 && m.pour(new MaterialStack(Mats.MAT_TUNGSTEN,0))==0 && m.pour(new MaterialStack(Mats.MAT_TUNGSTEN,-1))==0,"invalid offers reject");
        check(m.pour(new MaterialStack(Mats.MAT_TUNGSTEN,215))==215,"215 accepted");
        for(int i=0;i<210;i++) m.updateEntity();
        check(m.slots.get(1).isEmpty() && m.cooloff==200 && m.amount==215,"partial never cools");
        check(m.takeMold().isEmpty(),"partial prevents mold removal");
        MaterialStack offered=new MaterialStack(Mats.MAT_TUNGSTEN,50);
        check(m.pour(offered)==1 && offered.amount==50,"oversized offer accepted remainder only without mutation");
        check(m.pour(new MaterialStack(Mats.MAT_TUNGSTEN,216))==0,"full repeat rejects");
        for(int i=0;i<199;i++) m.updateEntity();
        check(m.slots.get(1).isEmpty() && m.cooloff==1,"199 full ticks no output");
        m.updateEntity(); check(m.slots.get(1).is(NtmItems.BLADE_TUNGSTEN.get()) && m.slots.get(1).getCount()==1,"200th full tick one blade");
        check(m.amount==0 && m.type==null && m.cooloff==200,"completion resets");
        check(m.pour(new MaterialStack(Mats.MAT_TUNGSTEN,216))==0,"output blocks pour");
        check(m.canTakeItemThroughFace(1,m.slots.get(1),Direction.DOWN) && !m.canTakeItemThroughFace(0,m.slots.get(0),Direction.DOWN),"automation output only");
        check(m.getSlotsForFace(Direction.DOWN).length==1 && m.getSlotsForFace(Direction.DOWN)[0]==1 && !m.canPlaceItem(0,new ItemStack(NtmItems.MOLD_BLADE.get())),"no automated mold insertion");
        check(m.removeItem(1,1).is(NtmItems.BLADE_TUNGSTEN.get()),"manual/automation inventory removal");
        check(m.pour(new MaterialStack(Mats.MAT_TUNGSTEN,300))==216,"next cast oversized bounded");
        ItemStack scraps=m.takeScraps(); MaterialStack scrapMat=com.hbm.items.CopperScrapsItem.getMats(scraps);
        check(scrapMat.material==Mats.MAT_TUNGSTEN && scrapMat.amount==216 && m.amount==0 && m.cooloff==200,"scraps retain exact material account");
        check(m.takeMold().component().equals("mold-components"),"reusable undamaged mold components retained");
        ItemStack stack=new ItemStack(NtmItems.MOLD_BLADE.get(),2).component("split-components");
        check(m.insertMold(stack) && stack.getCount()==1 && stack.component().equals("split-components") && m.slots.get(0).component().equals("split-components"),"split insertion preserves both components");
        Level client=level(); client.isClientSide=true; FoundryMoldBlockEntity cm=blade(client,9);
        check(cm.pour(new MaterialStack(Mats.MAT_TUNGSTEN,216))==0,"client pour rejected");
        cm.amount=216; cm.type=Mats.MAT_TUNGSTEN; cm.updateEntity();
        check(cm.slots.get(1).isEmpty() && cm.cooloff==200,"client does not process");
    }
    private static void invoke(FoundryMoldBlockEntity m,String name,CompoundTag tag) {
        try { var method=m.getClass().getDeclaredMethod(name,CompoundTag.class,net.minecraft.core.HolderLookup.Provider.class); method.setAccessible(true); method.invoke(m,tag,null); }
        catch(ReflectiveOperationException e) { throw new AssertionError(e); }
    }
    private static void persistence() {
        Level l=level(); FoundryMoldBlockEntity m=blade(l,10);
        m.pour(new MaterialStack(Mats.MAT_TUNGSTEN,100)); CompoundTag t=new CompoundTag(); invoke(m,"saveAdditional",t);
        FoundryMoldBlockEntity n=mold(l,11); invoke(n,"loadAdditional",t);
        check(n.amount==100 && n.type==Mats.MAT_TUNGSTEN && n.slots.get(0).component().equals("mold-components"),"partial save/load retains components");
        RegistryFriendlyByteBuf partialPacket=new RegistryFriendlyByteBuf(); n.serialize(partialPacket); FoundryMoldBlockEntity partialClient=mold(l,15); partialClient.deserialize(partialPacket);
        check(partialClient.amount==100 && partialClient.type==Mats.MAT_TUNGSTEN && partialClient.cooloff==200 && partialClient.slots.get(0).component().equals("mold-components"),"partial sync retains shape/material/components");
        n.pour(new MaterialStack(Mats.MAT_TUNGSTEN,116)); for(int i=0;i<37;i++) n.updateEntity();
        CompoundTag full=new CompoundTag(); invoke(n,"saveAdditional",full); FoundryMoldBlockEntity resumed=mold(l,12); invoke(resumed,"loadAdditional",full);
        check(resumed.cooloff==163 && resumed.amount==216,"saved cooloff restored");
        RegistryFriendlyByteBuf b=new RegistryFriendlyByteBuf(); resumed.serialize(b); FoundryMoldBlockEntity synced=mold(l,13); synced.deserialize(b);
        check(synced.amount==216 && synced.type==Mats.MAT_TUNGSTEN && synced.cooloff==163 && synced.slots.get(0).component().equals("mold-components"),"sync same shape/material/capacity and components");
        for(int i=0;i<162;i++) resumed.updateEntity(); check(resumed.slots.get(1).isEmpty(),"resumed requires remaining full ticks"); resumed.updateEntity(); check(resumed.slots.get(1).is(NtmItems.BLADE_TUNGSTEN.get()),"resumed cast completes");
        for(int id : new int[]{Mats.MAT_DURA.id,Mats.MAT_COPPER.id,-999}) {
            CompoundTag invalid=t.copy(); invalid.putInt("type",id); invoke(n,"loadAdditional",invalid);
            check(n.amount==0 && n.type==null,"invalid saved material rejects");
            RegistryFriendlyByteBuf packet=new RegistryFriendlyByteBuf(); packet.writeInt(500); packet.writeInt(-9); packet.writeInt(id); ItemStack.OPTIONAL_STREAM_CODEC.encode(packet,new ItemStack(NtmItems.MOLD_BLADE.get())); ItemStack.OPTIONAL_STREAM_CODEC.encode(packet,ItemStack.EMPTY); n.deserialize(packet);
            check(n.amount==0 && n.type==null && n.cooloff==1,"invalid sync material rejects and cooloff clamps");
        }
        CompoundTag over=t.copy(); over.putInt("amount",999); over.putInt("cooloff",999); invoke(n,"loadAdditional",over);
        check(n.amount==216 && n.cooloff==200,"blade NBT clamps capacity and cooloff");
        over.putInt("amount",-1); invoke(n,"loadAdditional",over); check(n.amount==0,"negative save amount clamps");
        RegistryFriendlyByteBuf oversized=new RegistryFriendlyByteBuf(); oversized.writeInt(999); oversized.writeInt(999); oversized.writeInt(Mats.MAT_TUNGSTEN.id); ItemStack.OPTIONAL_STREAM_CODEC.encode(oversized,new ItemStack(NtmItems.MOLD_BLADE.get())); ItemStack.OPTIONAL_STREAM_CODEC.encode(oversized,new ItemStack(NtmItems.BLADE_TUNGSTEN.get()).component("output-components")); n.deserialize(oversized);
        check(n.amount==216 && n.cooloff==200 && n.slots.get(1).component().equals("output-components"),"valid sync clamps and preserves output components");
        for(var material : List.of(Mats.MAT_COPPER,Mats.MAT_TUNGSTEN,Mats.MAT_STEEL,Mats.MAT_DURA)) {
            FoundryMoldBlockEntity old=mold(l,20); old.insertMold(new ItemStack(NtmItems.MOLD_PLATE_CAST.get()).component("old-components")); old.pour(new MaterialStack(material,100));
            CompoundTag legacy=new CompoundTag(); invoke(old,"saveAdditional",legacy); legacy.remove("cooloff"); FoundryMoldBlockEntity restored=mold(l,21); invoke(restored,"loadAdditional",legacy);
            check(restored.amount==100 && restored.type==material && restored.cooloff==200 && restored.slots.get(0).component().equals("old-components"),"all valid old plate saves without cooloff remain supported");
        }
    }
    private static void finite() {
        Level l=level(); BlockPos cp=new BlockPos(0,1,0), mp=new BlockPos(0,0,-2);
        MachineCrucibleBlockEntity c=new MachineCrucibleBlockEntity(cp,new BlockState()); l.put(c);
        FoundryMoldBlockEntity m=new FoundryMoldBlockEntity(mp,new BlockState()); l.put(m); m.insertMold(new ItemStack(NtmItems.MOLD_BLADE.get()));
        BlockState st=new BlockState(); st.facing=Direction.NORTH; l.states.put(cp,st);
        l.columnHits.put("0,-2",new BlockHitResult(HitResult.Type.BLOCK,mp,Direction.UP));
        c.heat=MachineCrucibleBlockEntity.MAX_HEAT; c.recipeStack.add(new MaterialStack(Mats.MAT_TUNGSTEN,1728));
        int blades=0;
        for(int batch=0;batch<8;batch++) {
            for(int pour=0;pour<9;pour++) { c.updateEntity(); l.time++; }
            check(m.amount==216 && MachineCrucibleBlockEntity.getQuantaFromType(c.recipeStack,Mats.MAT_TUNGSTEN)==1728-(batch+1)*216,"actual crucible debits only accepted 24q per tick");
            c.updateEntity(); l.time++; check(m.amount==216 && MachineCrucibleBlockEntity.getQuantaFromType(c.recipeStack,Mats.MAT_TUNGSTEN)==1728-(batch+1)*216,"full mold preserves crucible remainder");
            for(int i=0;i<200;i++) m.updateEntity();
            c.updateEntity(); l.time++; check(MachineCrucibleBlockEntity.getQuantaFromType(c.recipeStack,Mats.MAT_TUNGSTEN)==1728-(batch+1)*216,"blocked output preserves remainder");
            ItemStack out=m.removeItem(1,1); check(out.is(NtmItems.BLADE_TUNGSTEN.get()) && out.getCount()==1,"one output each finite batch"); blades+=out.getCount();
        }
        check(blades==8 && MachineCrucibleBlockEntity.getQuantaFromType(c.recipeStack,Mats.MAT_TUNGSTEN)==0 && 1728/72==24,"finite 24 ingots gives eight blades without replenishment");
        check(m.slots.get(0).is(NtmItems.MOLD_BLADE.get()),"same reusable mold all eight casts");
    }
    private static final class Slot implements IRecipeSlotBuilder {
        final List<ItemStack> stacks=new ArrayList<>();
        public IRecipeSlotBuilder addItemStack(ItemStack s){stacks.add(s);return this;}
        public IRecipeSlotBuilder addRichTooltipCallback(IRecipeSlotRichTooltipCallback cb){return this;}
    }
    private static final class Layout implements IRecipeLayoutBuilder {
        final List<Slot> slots=new ArrayList<>();
        public IRecipeSlotBuilder addSlot(RecipeIngredientRole role,int x,int y){Slot s=new Slot();slots.add(s);return s;}
    }
    private static void jei() {
        IGuiHelper gui=new IGuiHelper(){
            public IDrawable createDrawableItemLike(net.minecraft.world.level.ItemLike i){return new IDrawable(){};}
            public IDrawableBuilder drawableBuilder(ResourceLocation t,int u,int v,int w,int h){return new IDrawableBuilder(){public IDrawableBuilder setTextureSize(int w,int h){return this;}public IDrawable build(){return new IDrawable(){};}};}
        };
        var rows=CrucibleCastingRecipeHandler.getRecipes(); check(rows.size()==6,"exact six rows");
        var expected=List.of(Mats.MAT_COPPER,Mats.MAT_TUNGSTEN,Mats.MAT_STEEL,Mats.MAT_DURA,Mats.MAT_DURA,Mats.MAT_TUNGSTEN);
        var handler=new CrucibleCastingRecipeHandler(gui);
        for(int i=0;i<6;i++) {
            var row=rows.get(i); check(row.material()==expected.get(i) && row.ingot()==(i==4) && row.blade()==(i==5),"ordered old four plates, Dura, blade");
            Layout layout=new Layout(); handler.setRecipe(layout,row,null);
            MaterialStack liquid=com.hbm.items.CopperScrapsItem.getMats(layout.slots.get(0).stacks.get(0));
            check(liquid.material==expected.get(i) && liquid.amount==(i==4?72:216),"finite liquid amount each row");
            if(i==5) check(layout.slots.get(1).stacks.get(0).is(NtmItems.MOLD_BLADE.get()) && layout.slots.get(2).stacks.get(0).is(com.hbm.blocks.NtmBlocks.FOUNDRY_MOLD.asItem()) && layout.slots.get(3).stacks.get(0).is(NtmItems.BLADE_TUNGSTEN.get()),"blade mold foundry and actual output");
        }
        check(!new CrucibleCastingRecipeHandler.Casting(Mats.MAT_COPPER).ingot() && new CrucibleCastingRecipeHandler.Casting(Mats.MAT_DURA,true).ingot(),"legacy Casting constructor compatibility");
    }
    public static void main(String[] args) { smithing(); bounds(); persistence(); finite(); jei(); System.out.println("Goal 17A acquisition: "+checks+" assertions passed"); }
}
